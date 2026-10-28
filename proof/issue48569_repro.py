import asyncio,json,logging,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from litellm.proxy.mcp_server.mcp_server_manager import MCPServerManager
from litellm.types.mcp_server.mcp_server_manager import MCPServer
from litellm.types.mcp import MCPAuth
from litellm.proxy._types import MCPTransport
from litellm._logging import verbose_logger
requests=[]
class H(BaseHTTPRequestHandler):
 def do_POST(self):
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  requests.append((body.get('method'),self.headers.get('Authorization')))
  if self.headers.get('Authorization')!='Bearer test-upstream':
   self.send_response(401);self.send_header('WWW-Authenticate','Bearer');self.send_header('Content-Length','0');self.end_headers();return
  if 'id'not in body:self.send_response(202);self.send_header('Content-Length','0');self.end_headers();return
  method=body['method']
  result={'protocolVersion':'2025-03-26','capabilities':{'tools':{}},'serverInfo':{'name':'test','version':'1'}} if method=='initialize' else {'tools':[{'name':'read_note','description':'test','inputSchema':{'type':'object'}}]}
  data=json.dumps({'jsonrpc':'2.0','id':body['id'],'result':result}).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 def log_message(self,*a):pass
server=ThreadingHTTPServer(('127.0.0.1',0),H);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
async def main():
 manager=MCPServerManager();s=MCPServer(server_id='delegate',name='delegate',url=f'http://127.0.0.1:{server.server_port}/mcp',transport=MCPTransport.http,auth_type=MCPAuth.oauth_delegate)
 manager.registry[s.server_id]=s
 await manager._initialize_tool_name_to_mcp_server_name_mapping();print('STARTUP_REQUESTS',requests)
 assert requests==[], 'Unauthenticated startup discovery was not skipped'
 tools=await manager.get_tools_from_server(s,mcp_auth_header='Bearer test-upstream');print('LATER_TOOLS',[t.name for t in tools]);print('ALL_REQUESTS',requests)
 assert [t.name for t in tools]==['delegate-read_note']
 assert requests and all(token=='Bearer test-upstream' for _,token in requests)
try:asyncio.run(main())
finally:server.shutdown();thread.join()
