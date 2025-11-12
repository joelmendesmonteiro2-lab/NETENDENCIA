import http.server
import socketserver
import webbrowser
import os

class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Serve o arquivo index.html para todas as rotas
        if self.path != '/':
            self.path = '/' + self.path.split('/')[-1]
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

def main():
    PORT = 8080
    
    # Verifica se os arquivos existem
    if not os.path.exists('index.html'):
        print("Erro: arquivo index.html não encontrado!")
        return
    
    # Configura o servidor
    with socketserver.TCPServer(("", PORT), MyHttpRequestHandler) as httpd:
        print(f" Servidor rodando em http://localhost:{PORT}")
        print("📱 Abrindo no navegador...")
        webbrowser.open(f'http://localhost:{PORT}')
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print(" Servidor encerrado!")

if _name_ == "_main_":
    main()