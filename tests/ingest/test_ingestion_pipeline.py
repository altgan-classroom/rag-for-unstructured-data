import pytest
from unittest.mock import patch, MagicMock
from core.ingest.tasks import scan_and_enqueue_documents, process_queued_document

@pytest.mark.celery
@patch('core.ingest.tasks.BaseConnector')
@patch('core.ingest.tasks.process_queued_document')
def test_scan_and_enqueue_documents(mock_process_queued_document, mock_base_connector):
    # Arrange
    mock_connector_instance = MagicMock()
    mock_base_connector.from_config.return_value = mock_connector_instance
    mock_connector_instance.get_all_documents.return_value = [
        {
            'doc_name': '1211523415_20130700_CCS1_Periodic_Report_Mechanical_Integrity_bb', 
            'url': 'https://orca-rag-documents.s3.amazonaws.com/oil-and-gas/1211523415_20130700_CCS1_Periodic_Report_Mechanical_Integrity_bb.pdf',
            'content_type': 'pdf', 'size': 384.72,
            'permissions': {'grants': [{'grantee': 'Public'}]},
            
        },
        {
            'doc_name': '1211523460_VW1_Completion_Report_D2', 
            'url': 'https://orca-rag-documents.s3.amazonaws.com/oil-and-gas/1211523460_VW1_Completion_Report_D2.pdf',
            'content_type': 'pdf', 'size': 7009.92,
            'permissions': {'grants': [{'grantee': 'IBDBProduction'}]},
        },
        {
            'doc_name': '1Geophysical_Well-GM2-2017_070617', 
            'url': 'https://orca-rag-documents.s3.amazonaws.com/oil-and-gas/Geophysical_Well-GM2-2017_070617.pdf',
            'content_type': 'pdf', 'size': 667.68,
            'permissions': {'grants': [{'grantee': 'IBDPSeismic'}]},
        },

    ]

    connector_config = {'some_config': 'value'}
    
    # Act
    result = scan_and_enqueue_documents(connector_config=connector_config)

    # Assert
    assert result['total_documents'] == 3
    assert mock_process_queued_document.delay.call_count == 3

@pytest.mark.celery
@patch('core.ingest.tasks.BaseConnector')
@patch('core.ingest.tasks.SupabaseClient')
@patch('core.ingest.tasks.markitdown_extract')
@patch('core.ingest.tasks.QdrantDB')
def test_process_queued_document(mock_qdrant_db, mock_markitdown_extract, mock_supabase_client, mock_base_connector):
    # Arrange
    mock_connector_instance = MagicMock()
    mock_base_connector.from_config.return_value = mock_connector_instance
    mock_markitdown_extract.return_value = MagicMock(content='# Sample Markdown')
    
    document = {
        'doc_name': '1211523415_20130700_CCS1_Periodic_Report_Mechanical_Integrity_bb', 
        'url': 'https://orca-rag-documents.s3.amazonaws.com/oil-and-gas/1211523415_20130700_CCS1_Periodic_Report_Mechanical_Integrity_bb.pdf',
        'content_type': 'pdf', 'size': 384.72,
        'permissions': {'grants': [{'grantee': 'Public'}]},
    }
    connector_config = {'some_config': 'value'}
    
    # Act
    result = process_queued_document(document=document, connector_config=connector_config)

    # Assert
    assert result is True
    mock_markitdown_extract.assert_called_once()
    mock_qdrant_db().add_documents.assert_called_once()
