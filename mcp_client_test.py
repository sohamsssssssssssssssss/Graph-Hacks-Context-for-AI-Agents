"""Live six-tool MCP stdio smoke test: python3.11 mcp_client_test.py."""
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    root=Path(__file__).resolve().parent
    server=subprocess.Popen([sys.executable,str(root/'mcp_server.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,cwd=root,env={**os.environ,'KEYSTONE_ACTION_REQUEST':'1'})
    request_id=0
    def call(method,params=None):
        nonlocal request_id
        request_id+=1
        server.stdin.write(json.dumps({'jsonrpc':'2.0','id':request_id,'method':method,'params':params or {}})+'\n')
        server.stdin.flush()
        line=server.stdout.readline()
        assert line,'server terminated before responding'
        response=json.loads(line)
        assert response['id']==request_id and 'error' not in response,response
        return response['result']
    try:
        assert call('initialize',{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'keystone-smoke','version':'1'}})['protocolVersion']=='2025-11-25'
        server.stdin.write(json.dumps({'jsonrpc':'2.0','method':'notifications/initialized'})+'\n');server.stdin.flush()
        assert len(call('tools/list')['tools'])==6
        calls=[('blast_radius',{'service':'redis-cluster'}),
               ('criticality',{'services':['api-hub-service','batch-exporter-service']}),
               ('rank_owners',{'service':'notifier'}),
               ('trace_decision',{'topic':'session-cache-storage'}),
               ('verify_path',{'claim':{'edge_ids':['EID-S8-01']},'target':'ledger','purpose':'ACT'})]
        results={}
        for name,args in calls:
            value=call('tools/call',{'name':name,'arguments':args})
            assert not value.get('isError'),value
            results[name]=value['structuredContent']
        receipt=results['verify_path']
        value=call('tools/call',{'name':'propose_action','arguments':{'pass_id':receipt['pass_id'],'action':receipt['action'],'execute':False}})
        assert not value.get('isError'),value
        results['propose_action']=value['structuredContent']
        assert results['blast_radius']['count']==9
        assert results['criticality']['escalation_order']==['service-api-hub','service-batch-exporter']
        assert results['rank_owners']['contested']
        assert any(e['eid']=='EID-S1-05' for e in results['trace_decision']['chain'])
        assert results['propose_action']['dry_run'] and not results['propose_action']['executed']
        print(json.dumps({'tools_called':list(results),'passed':6,'failed':0,
                          'pagerank_algorithm':results['criticality']['algorithm']}))
    finally:
        server.stdin.close()
        try:server.wait(timeout=10)
        except subprocess.TimeoutExpired:server.kill();server.wait()


if __name__=='__main__':
    main()
