"""MCP 2025-11-25 stdio server. stdout contains protocol messages only."""
import inspect
import json
import sys

from app.tools import runtime

STRING = {"type":"string"}
ACTION = {"type":"object","properties":{"kind":{"enum":["ACT","PAGE","READ"]},"target":STRING,"recipient":STRING},
          "required":["kind","target"],"additionalProperties":False}
CLAIM = {"type":"object","properties":{"edge_ids":{"type":"array","items":STRING,"minItems":1,"maxItems":8},
         "start":STRING,"action":ACTION},"additionalProperties":False}
SPECS = {
    "blast_radius": ({"service":STRING}, ["service"], "Distinct current, accessible dependents and minimum depths."),
    "criticality": ({"services":{"type":"array","items":STRING,"maxItems":100}}, ["services"], "Authorized current-edge PageRank and descending escalation order."),
    "rank_owners": ({"service":STRING}, ["service"], "Current owners, explicit contested sides, verified on-call and fallback."),
    "trace_decision": ({"topic":STRING}, ["topic"], "Accessible dated decision history; historical statuses are explicit."),
    "ownership_history": ({"service":STRING,"as_of":{"type":["string","null"]}}, ["service"], "READ-only ownership, approvals and disputes, including labeled rejected/history evidence. Optional ISO timestamp recomputes past ownership; never authorizes ACT."),
    "verify_path": ({"claim":CLAIM,"target":STRING,"purpose":{"enum":["ACT","READ"]}}, ["claim","target","purpose"], "Recheck evidence and mint a target/action-bound, expiring single-use pass."),
    "propose_action": ({"pass_id":{"type":["string","null"]},"action":ACTION,"execute":{"type":"boolean","default":False}},
                       ["pass_id","action"], "Dry-run by default. Execution records a local audit, not external delivery."),
}


def validate(value, schema):
    kind = schema.get("type")
    types = kind if isinstance(kind,list) else [kind]
    checks = {"string":lambda x:isinstance(x,str), "null":lambda x:x is None,
              "boolean":lambda x:isinstance(x,bool),"array":lambda x:isinstance(x,list),"object":lambda x:isinstance(x,dict)}
    if kind and not any(checks[t](value) for t in types):
        raise ValueError("argument type mismatch")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("argument enum mismatch")
    if isinstance(value,dict) and kind=="object":
        props=schema.get("properties",{})
        if not set(schema.get("required",[])) <= set(value) or (not schema.get("additionalProperties",True) and set(value)-set(props)):
            raise ValueError("unknown or missing argument")
        for key,sub in props.items():
            if key in value:validate(value[key],sub)
    if isinstance(value,list) and kind=="array":
        if len(value)>schema.get("maxItems",len(value)) or len(value)<schema.get("minItems",0):
            raise ValueError("array length out of bounds")
        for item in value:validate(item,schema["items"])


def serve(input_stream=sys.stdin,output_stream=sys.stdout,backend_factory=runtime):
    initialized=False
    for line in input_stream:
        request=None
        try:
            request=json.loads(line)
            if not isinstance(request,dict) or request.get("jsonrpc")!="2.0" or not isinstance(request.get("method"),str):
                raise ValueError("invalid JSON-RPC request")
            method=request["method"]
            if "id" not in request:
                continue
            if method=="initialize":
                initialized=True
                result={"protocolVersion":"2025-11-25","capabilities":{"tools":{}},
                        "serverInfo":{"name":"keystone-tools","version":"0.1.0"}}
            elif not initialized:
                raise ValueError("initialize required")
            elif method=="ping":
                result={}
            elif method=="tools/list":
                result={"tools":[{"name":name,"description":description,"inputSchema":{"type":"object","properties":props,
                        "required":required,"additionalProperties":False}}
                        for name,(props,required,description) in SPECS.items()]}
            elif method=="tools/call":
                params=request.get("params",{})
                if not isinstance(params,dict):
                    raise ValueError("invalid parameters")
                name=params.get("name")
                if name not in SPECS:
                    raise ValueError("unknown tool")
                props,required,_=SPECS[name]
                arguments=params.get("arguments",{})
                validate(arguments,{"type":"object","properties":props,"required":required,"additionalProperties":False})
                try:
                    function=getattr(backend_factory(),name)
                    inspect.signature(function).bind(**arguments)
                    value=function(**arguments)
                    result={"content":[{"type":"text","text":json.dumps(value,ensure_ascii=False)}],
                            "structuredContent":value,"isError":value.get("ok") is False}
                except Exception:
                    # Connection/driver details can contain hidden IDs, queries or credentials.
                    value={"ok":False,"outcome":"ESCALATE","reason":"tool unavailable or request rejected","evidence":[]}
                    result={"content":[{"type":"text","text":json.dumps(value)}],"structuredContent":value,"isError":True}
            else:
                response={"jsonrpc":"2.0","id":request["id"],"error":{"code":-32601,"message":"method not found"}}
                output_stream.write(json.dumps(response)+"\n");output_stream.flush();continue
            response={"jsonrpc":"2.0","id":request["id"],"result":result}
        except (ValueError,TypeError,KeyError):
            response={"jsonrpc":"2.0","id":request.get("id") if isinstance(request,dict) else None,
                      "error":{"code":-32602 if request else -32700,"message":"invalid request or arguments"}}
        output_stream.write(json.dumps(response,ensure_ascii=False)+"\n")
        output_stream.flush()


if __name__=="__main__":
    serve()
