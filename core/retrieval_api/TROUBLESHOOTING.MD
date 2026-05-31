## Error trace1:

```
ERROR: Exception:
Traceback (most recent call last):
  File "/Users/sai/Orca/rag-api/lib/python3.8/site-packages/pip/_internal/cli/base_command.py", line 106, in _run_wrapper
    status = _inner_run()
  File "/Users/sai/Orca/rag-api/lib/python3.8/site-packages/pip/_internal/cli/base_command.py", line 97, in _inner_run
    return self.run(options, args)
  File "/Users/sai/Orca/rag-api/lib/python3.8/site-packages/pip/_internal/cli/req_command.py", line 67, in wrapper
    return func(self, options, args)
  File "/Users/sai/Orca/rag-api/lib/python3.8/site-packages/pip/_internal/commands/install.py", line 386, in run
    requirement_set = resolver.resolve(
  File "/Users/sai/Orca/rag-api/lib/python3.8/site-packages/pip/_internal/resolution/resolvelib/resolver.py", line 95, in resolve
    result = self._result = resolver.resolve(
  File "/Users/sai/Orca/rag-api/lib/python3.8/site-packages/pip/_vendor/resolvelib/resolvers.py", line 546, in resolve
    state = resolution.resolve(requirements, max_rounds=max_rounds)
  File "/Users/sai/Orca/rag-api/lib/python3.8/site-packages/pip/_vendor/resolvelib/resolvers.py", line 457, in resolve
    raise ResolutionTooDeep(max_rounds)
pip._vendor.resolvelib.resolvers.ResolutionTooDeep: 200000
```

changed to named versions and the error got solved.




