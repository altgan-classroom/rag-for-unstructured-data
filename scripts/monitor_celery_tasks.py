#!/usr/bin/env python3
"""
CLI tool to monitor Celery tasks with enhanced debugging.
"""
import argparse
import json
import logging
import os
import sys
import redis
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def get_redis_connection():
    """Get a Redis connection using environment variables."""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    try:
        return redis.Redis.from_url(redis_url, decode_responses=False)
    except Exception as e:
        logger.error(f"Failed to connect to Redis at {redis_url}: {str(e)}")
        sys.exit(1)

def get_task_result(redis_conn, task_id: str) -> Dict[str, Any]:
    """Get the result of a specific task by its ID."""
    try:
        result_key = f'celery-task-meta-{task_id}'.encode('utf-8')
        result_data = redis_conn.get(result_key)
        
        if not result_data:
            return {
                'task_id': task_id,
                'status': 'NOT_FOUND',
                'error': 'Task result not found in Redis. It may have expired or never completed.'
            }
            
        result = json.loads(result_data)
        response = {
            'task_id': task_id,
            'status': result.get('status'),
            'result': result.get('result', None),
            'completion_time': result.get('date_done', None)
        }
        
        # Only add error and traceback if they exist
        if 'error' in result:
            response['error'] = result['error']
        if 'traceback' in result:
            response['traceback'] = result['traceback']
            
        return response
    except Exception as e:
        return {
            'task_id': task_id,
            'status': 'ERROR',
            'error': f'Failed to fetch task result: {str(e)}'
        }

def get_completed_tasks(redis_conn, limit: int = 10) -> Dict[str, Any]:
    """Get a list of recently completed tasks from Redis."""
    try:
        # Get all task result keys
        keys = redis_conn.keys('celery-task-meta-*')
        logger.info(f"Found {len(keys)} task result keys in Redis")
        
        # Sort by most recent first (assuming task IDs are time-based)
        keys.sort(reverse=True)
        
        tasks = []
        for key in keys[:limit]:
            task_id = key.decode('utf-8').replace('celery-task-meta-', '')
            tasks.append(get_task_result(redis_conn, task_id))
            
        return {
            'count': len(tasks),
            'tasks': tasks
        }
    except Exception as e:
        logger.error(f"Error fetching completed tasks: {str(e)}")
        return {
            'error': str(e),
            'tasks': []
        }

def main():
    parser = argparse.ArgumentParser(description='Monitor Celery tasks with enhanced debugging')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Parser for getting task by ID
    get_parser = subparsers.add_parser('get', help='Get task by ID')
    get_parser.add_argument('task_id', help='Task ID to look up')
    
    # Parser for listing completed tasks
    list_parser = subparsers.add_parser('list', help='List completed tasks')
    list_parser.add_argument('--limit', type=int, default=10, 
                           help='Maximum number of tasks to show (default: 10)')
    list_parser.add_argument('--debug', action='store_true',
                           help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    if not args.command:
        parser.print_help()
        return
    
    redis_conn = get_redis_connection()
    
    try:
        if args.command == 'get':
            result = get_task_result(redis_conn, args.task_id)
            print(f"Task ID: {result['task_id']}")
            print(f"Status: {result.get('status', 'UNKNOWN')}")
            if 'result' in result:
                print("Result:")
                print(json.dumps(result['result'], indent=2))
            if 'completion_time' in result:
                print(f"Completion Time: {result['completion_time']}")
            if 'error' in result:
                print(f"Error: {result['error']}")
            
        elif args.command == 'list':
            result = get_completed_tasks(redis_conn, limit=args.limit)
            print(f"Found {result.get('count', 0)} tasks in Redis:\n")
            for task in result.get('tasks', []):
                print(f"Task ID: {task['task_id']}")
                print(f"Status: {task.get('status', 'UNKNOWN')}")
                if 'result' in task:
                    print("Result:")
                    print(json.dumps(task['result'], indent=2))
                if 'completion_time' in task:
                    print(f"Completion Time: {task['completion_time']}")
                if 'error' in task:
                    print(f"Error: {task['error']}")
                print(20*"-")
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
