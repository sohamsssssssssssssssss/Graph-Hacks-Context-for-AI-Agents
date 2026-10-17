import io
import json

from mcp_server import SPECS, serve


def test_mcp_handshake_and_schema_validation():
    requests=[{'jsonrpc':'2.0','id':1,'method':'initialize'},
              {'jsonrpc':'2.0','method':'notifications/initialized'},
              {'jsonrpc':'2.0','id':2,'method':'tools/list'},
              {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'blast_radius','arguments':{'service':'ledger','cypher':'DELETE'}}}]
    output=io.StringIO()
    serve(io.StringIO('\n'.join(map(json.dumps,requests))+'\n'),output,lambda:None)
    replies=[json.loads(line) for line in output.getvalue().splitlines()]
    assert len(replies)==3
    assert len(replies[1]['result']['tools'])==len(SPECS)==6
    assert replies[2]['error']['code']==-32602


def test_mcp_requires_initialize_and_masks_driver_errors():
    class Backend:
        def blast_radius(self,service):raise RuntimeError('hidden DOC-PM-S6 password=secret')
    requests=[{'jsonrpc':'2.0','id':1,'method':'tools/list'},
              {'jsonrpc':'2.0','id':2,'method':'initialize'},
              {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'blast_radius','arguments':{'service':'ledger'}}}]
    output=io.StringIO()
    serve(io.StringIO('\n'.join(map(json.dumps,requests))),output,Backend)
    assert 'DOC-PM-S6' not in output.getvalue() and 'password' not in output.getvalue()
    replies=[json.loads(line) for line in output.getvalue().splitlines()]
    assert 'error' in replies[0] and replies[-1]['result']['isError']
