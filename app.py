from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
import json
import random
import sqlite3
import os
from contextlib import contextmanager

app = Flask(__name__)
app.secret_key = 'neteNDENCIA_secret_key_2025'
app.config['TEMPLATES_AUTO_RELOAD'] = True

# ========== CONFIGURAÇÃO DO BANCO DE DADOS ==========

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('neteNDENCIA.db')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Tabela de famílias
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS familias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                codigo_familia TEXT UNIQUE
            )
        ''')
        
        # Tabela de usuários - COM COLUNA RELACIONAMENTO ADICIONADA
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                idade INTEGER,
                familia_id INTEGER,
                email TEXT UNIQUE,
                senha TEXT,
                relacionamento TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (familia_id) REFERENCES familias (id)
            )
        ''')
        
        # Tabela de perguntas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS perguntas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                texto TEXT NOT NULL,
                categoria TEXT
            )
        ''')
        
        # Tabela de opções de resposta
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS opcoes_resposta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pergunta_id INTEGER,
                texto TEXT NOT NULL,
                pontuacao INTEGER,
                FOREIGN KEY (pergunta_id) REFERENCES perguntas (id)
            )
        ''')
        
        # Tabela de diagnósticos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diagnosticos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                pontuacao INTEGER,
                nivel TEXT,
                data_diagnostico TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                respostas TEXT,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        ''')
        
        # Tabela de reflexões
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reflexoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                pergunta TEXT,
                resposta TEXT,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        ''')
        
        conn.commit()
        print("✅ Banco de dados inicializado com sucesso!")

def atualizar_schema():
    """Atualiza o schema do banco de dados para adicionar colunas faltantes"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            # Verificar se a coluna 'relacionamento' existe na tabela usuarios
            cursor.execute("PRAGMA table_info(usuarios)")
            colunas = [coluna[1] for coluna in cursor.fetchall()]
            
            if 'relacionamento' not in colunas:
                print("🔧 Adicionando coluna 'relacionamento' à tabela usuarios...")
                cursor.execute('ALTER TABLE usuarios ADD COLUMN relacionamento TEXT')
                conn.commit()
                print("✅ Coluna 'relacionamento' adicionada com sucesso!")
            else:
                print("✅ Coluna 'relacionamento' já existe na tabela usuarios")
            
        except Exception as e:
            print(f"❌ Erro ao atualizar schema: {e}")

def inserir_perguntas_iniciais():
    """Insere as 10 perguntas do questionário no banco"""
    perguntas = [
        {
            "texto": "Com que frequência você verifica seu smartphone sem um motivo específico?",
            "opcoes": [
                {"texto": "Menos de 5 vezes ao dia", "pontuacao": 0},
                {"texto": "Entre 5 e 10 vezes ao dia", "pontuacao": 1},
                {"texto": "Entre 11 e 20 vezes ao dia", "pontuacao": 2},
                {"texto": "Mais de 20 vezes ao dia", "pontuacao": 3}
            ]
        },
        {
            "texto": "Quanto tempo você passa em redes sociais diariamente?",
            "opcoes": [
                {"texto": "Menos de 30 minutos", "pontuacao": 0},
                {"texto": "Entre 30 minutos e 1 hora", "pontuacao": 1},
                {"texto": "Entre 1 e 2 horas", "pontuacao": 2},
                {"texto": "Mais de 2 horas", "pontuacao": 3}
            ]
        },
        {
            "texto": "Você já deixou de realizar tarefas importantes por estar usando dispositivos digitais?",
            "opcoes": [
                {"texto": "Nunca", "pontuacao": 0},
                {"texto": "Raramente", "pontuacao": 1},
                {"texto": "Às vezes", "pontuacao": 2},
                {"texto": "Frequentemente", "pontuacao": 3}
            ]
        },
        {
            "texto": "Como você se sente quando não tem acesso à internet?",
            "opcoes": [
                {"texto": "Normal, não me afeta", "pontuacao": 0},
                {"texto": "Um pouco incomodado(a)", "pontuacao": 1},
                {"texto": "Muito ansioso(a) ou irritado(a)", "pontuacao": 2},
                {"texto": "Incapaz de funcionar normalmente", "pontuacao": 3}
            ]
        },
        {
            "texto": "Você usa dispositivos digitais durante as refeições?",
            "opcoes": [
                {"texto": "Nunca", "pontuacao": 0},
                {"texto": "Raramente", "pontuacao": 1},
                {"texto": "Às vezes", "pontuacao": 2},
                {"texto": "Sempre ou quase sempre", "pontuacao": 3}
            ]
        },
        {
            "texto": "Você já tentou reduzir seu tempo de uso digital sem sucesso?",
            "opcoes": [
                {"texto": "Nunca tentei", "pontuacao": 0},
                {"texto": "Tentei e consegui reduzir", "pontuacao": 1},
                {"texto": "Tentei mas não consegui manter", "pontuacao": 2},
                {"texto": "Já tentei várias vezes sem sucesso", "pontuacao": 3}
            ]
        },
        {
            "texto": "O uso de dispositivos digitais afeta seu sono?",
            "opcoes": [
                {"texto": "Não, durmo bem", "pontuacao": 0},
                {"texto": "Às vezes demoro para dormir", "pontuacao": 1},
                {"texto": "Frequentemente durmo menos do que deveria", "pontuacao": 2},
                {"texto": "Sim, tenho insônia relacionada ao uso", "pontuacao": 3}
            ]
        },
        {
            "texto": "Você prioriza interações online em detrimento de interações presenciais?",
            "opcoes": [
                {"texto": "Nunca", "pontuacao": 0},
                {"texto": "Raramente", "pontuacao": 1},
                {"texto": "Às vezes", "pontuacao": 2},
                {"texto": "Frequentemente", "pontuacao": 3}
            ]
        },
        {
            "texto": "Como você descreveria seu controle sobre o uso de tecnologia?",
            "opcoes": [
                {"texto": "Tenho total controle", "pontuacao": 0},
                {"texto": "Tenho bom controle, com exceções", "pontuacao": 1},
                {"texto": "Às vezes perco o controle", "pontuacao": 2},
                {"texto": "Sinto que não tenho controle", "pontuacao": 3}
            ]
        },
        {
            "texto": "Você já mentiu sobre o tempo que passa online?",
            "opcoes": [
                {"texto": "Nunca", "pontuacao": 0},
                {"texto": "Raramente", "pontuacao": 1},
                {"texto": "Às vezes", "pontuacao": 2},
                {"texto": "Frequentemente", "pontuacao": 3}
            ]
        }
    ]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Verificar se já existem perguntas
        cursor.execute('SELECT COUNT(*) as count FROM perguntas')
        if cursor.fetchone()['count'] == 0:
            for pergunta_data in perguntas:
                # Inserir pergunta
                cursor.execute(
                    'INSERT INTO perguntas (texto, categoria) VALUES (?, ?)',
                    (pergunta_data['texto'], 'dependencia_digital')
                )
                pergunta_id = cursor.lastrowid
                
                # Inserir opções de resposta
                for opcao in pergunta_data['opcoes']:
                    cursor.execute(
                        'INSERT INTO opcoes_resposta (pergunta_id, texto, pontuacao) VALUES (?, ?, ?)',
                        (pergunta_id, opcao['texto'], opcao['pontuacao'])
                    )
            
            conn.commit()
            print("✅ Perguntas iniciais inseridas no banco!")

# ========== SERVIÇOS DE DIAGNÓSTICO ==========

class ServicoDiagnostico:
    @staticmethod
    def calcular_nivel(pontuacao):
        if pontuacao <= 15:
            return "Não dependente"
        elif pontuacao <= 25:
            return "Moderado"
        else:
            return "Dependente"
    
    @staticmethod
    def obter_solucoes_por_nivel(nivel):
        solucoes = {
            'Dependente': [
                "Estabeleça limites de tempo rigorosos para uso da internet",
                "Desative notificações de redes sociais durante o trabalho",
                "Pratique atividades offline como exercícios físicos ou leitura",
                "Busque apoio familiar para monitoramento",
                "Use aplicativos de controle de tempo de tela",
                "Estabeleça zonas livres de dispositivos em casa",
                "Procure ajuda profissional se necessário",
                "Participe de grupos de apoio online"
            ],
            'Moderado': [
                "Faça pausas regulares a cada 45 minutos de uso",
                "Estabeleça zonas livres de dispositivos em casa",
                "Pratique a técnica Pomodoro para melhor gestão do tempo",
                "Mantenha um diário de uso da internet",
                "Defina horários específicos para verificar redes sociais",
                "Pratique atividades físicas regularmente",
                "Estabeleça metas realistas de redução de tempo online",
                "Desenvolva hobbies offline"
            ],
            'Não dependente': [
                "Continue mantendo hábitos saudáveis de uso digital",
                "Compartilhe suas estratégias com familiares",
                "Periodicamente reavalie seu relacionamento com a tecnologia",
                "Mantenha atividades sociais e hobbies offline",
                "Ajude outros membros da família a alcançar o equilíbrio",
                "Continue com atividades físicas regulares",
                "Mantenha uma rotina equilibrada entre online e offline",
                "Comemore suas conquistas de equilíbrio digital"
            ]
        }
        return solucoes.get(nivel, [])
    
    @staticmethod
    def verificar_reavaliacao_necesaria(ultimo_diagnostico):
        if not ultimo_diagnostico:
            return True
        
        if isinstance(ultimo_diagnostico['data_diagnostico'], str):
            try:
                data_ultimo = datetime.fromisoformat(ultimo_diagnostico['data_diagnostico'].replace('Z', '+00:00'))
            except:
                data_ultimo = datetime.strptime(ultimo_diagnostico['data_diagnostico'], '%Y-%m-%d %H:%M:%S')
        else:
            data_ultimo = ultimo_diagnostico['data_diagnostico']
            
        return (datetime.now() - data_ultimo).days >= 30

# ========== ROTAS PRINCIPAIS ==========

@app.route('/')
def index():
    # Se não estiver logado, redirecionar para landing
    if 'usuario_id' not in session:
        return redirect('/landing')
    
    return render_template('index.html')

@app.route('/landing')
def landing():
    return render_template('landing.html')

# ========== API ENDPOINTS ==========

@app.route('/api/dashboard-data')
def api_dashboard_data():
    """API para fornecer dados do dashboard"""
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    
    usuario_id = session.get('usuario_id')
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Dados do usuário
            cursor.execute('SELECT * FROM usuarios WHERE id = ?', (usuario_id,))
            usuario = cursor.fetchone()
            
            if not usuario:
                return jsonify({'error': 'Usuário não encontrado'}), 404
            
            # Último diagnóstico
            cursor.execute('''
                SELECT * FROM diagnosticos 
                WHERE usuario_id = ? 
                ORDER BY data_diagnostico DESC 
                LIMIT 1
            ''', (usuario_id,))
            ultimo_diagnostico = cursor.fetchone()
            
            # Histórico para gráfico
            cursor.execute('''
                SELECT pontuacao, nivel, data_diagnostico 
                FROM diagnosticos 
                WHERE usuario_id = ? 
                ORDER BY data_diagnostico
            ''', (usuario_id,))
            historico = cursor.fetchall()
            
            # Dados da família
            familia_data = obter_dados_familia(cursor, usuario['familia_id']) if usuario and usuario['familia_id'] else {}
            
            # Dica do dia
            dica_do_dia = obter_dica_do_dia(cursor, usuario_id)
            
            # Verificar necessidade de reavaliação
            precisa_reavaliar = ServicoDiagnostico.verificar_reavaliacao_necesaria(
                dict(ultimo_diagnostico) if ultimo_diagnostico else None
            )
        
        return jsonify({
            'success': True,
            'usuario': dict(usuario),
            'ultimo_diagnostico': dict(ultimo_diagnostico) if ultimo_diagnostico else None,
            'historico': [dict(item) for item in historico],
            'familia_data': familia_data,
            'dica_do_dia': dica_do_dia,
            'precisa_reavaliar': precisa_reavaliar
        })
        
    except Exception as e:
        print(f"Erro no dashboard-data: {e}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@app.route('/api/perguntas')
def api_perguntas():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.id, p.texto, p.categoria, 
                       json_group_array(json_object('id', o.id, 'texto', o.texto, 'pontuacao', o.pontuacao)) as opcoes
                FROM perguntas p
                LEFT JOIN opcoes_resposta o ON p.id = o.pergunta_id
                GROUP BY p.id
                ORDER BY p.id
            ''')
            perguntas = cursor.fetchall()
        
        perguntas_formatadas = []
        for pergunta in perguntas:
            try:
                opcoes = json.loads(pergunta['opcoes']) if pergunta['opcoes'] else []
            except:
                opcoes = []
                
            perguntas_formatadas.append({
                'id': pergunta['id'],
                'texto': pergunta['texto'],
                'categoria': pergunta['categoria'],
                'opcoes': opcoes
            })
        
        return jsonify(perguntas_formatadas)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/diagnostico', methods=['POST'])
def api_salvar_diagnostico():
    try:
        data = request.json
        respostas = data.get('respostas', [])
        usuario_id = session.get('usuario_id', 1)
        
        # Calcular pontuação total
        pontuacao_total = sum(resposta['pontuacao'] for resposta in respostas)
        
        # Determinar nível
        nivel = ServicoDiagnostico.calcular_nivel(pontuacao_total)
        
        # Salvar diagnóstico
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO diagnosticos (usuario_id, pontuacao, nivel, respostas)
                VALUES (?, ?, ?, ?)
            ''', (usuario_id, pontuacao_total, nivel, json.dumps(respostas)))
            
            diagnostico_id = cursor.lastrowid
            conn.commit()
        
        # Obter soluções recomendadas
        solucoes = ServicoDiagnostico.obter_solucoes_por_nivel(nivel)
        
        return jsonify({
            'success': True,
            'diagnostico': {
                'id': diagnostico_id,
                'pontuacao': pontuacao_total,
                'nivel': nivel,
                'data_diagnostico': datetime.now().isoformat()
            },
            'solucoes': solucoes
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

# ========== NOVA ROTA PARA DIAGNÓSTICO FAMILIAR ==========

@app.route('/api/familia/membros/<int:membro_id>/diagnostico', methods=['POST'])
def api_salvar_diagnostico_familiar(membro_id):
    """API para salvar diagnóstico de um membro específico da família"""
    try:
        data = request.json
        respostas = data.get('respostas', [])
        usuario_id = session.get('usuario_id')
        
        if not usuario_id:
            return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401
        
        # Verificar se o membro pertence à mesma família
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u1.familia_id as usuario_familia, u2.familia_id as membro_familia
                FROM usuarios u1, usuarios u2 
                WHERE u1.id = ? AND u2.id = ?
            ''', (usuario_id, membro_id))
            resultado = cursor.fetchone()
            
            if not resultado or resultado['usuario_familia'] != resultado['membro_familia']:
                return jsonify({'success': False, 'error': 'Sem permissão para este membro'}), 403
        
        # Calcular pontuação total
        pontuacao_total = sum(resposta['pontuacao'] for resposta in respostas)
        
        # Determinar nível
        nivel = ServicoDiagnostico.calcular_nivel(pontuacao_total)
        
        # Salvar diagnóstico
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO diagnosticos (usuario_id, pontuacao, nivel, respostas)
                VALUES (?, ?, ?, ?)
            ''', (membro_id, pontuacao_total, nivel, json.dumps(respostas)))
            
            diagnostico_id = cursor.lastrowid
            conn.commit()
        
        # Obter soluções recomendadas
        solucoes = ServicoDiagnostico.obter_solucoes_por_nivel(nivel)
        
        return jsonify({
            'success': True,
            'diagnostico': {
                'id': diagnostico_id,
                'pontuacao': pontuacao_total,
                'nivel': nivel,
                'data_diagnostico': datetime.now().isoformat()
            },
            'solucoes': solucoes
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@app.route('/api/historico')
def api_historico():
    try:
        usuario_id = session.get('usuario_id', 1)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pontuacao, nivel, data_diagnostico 
                FROM diagnosticos 
                WHERE usuario_id = ? 
                ORDER BY data_diagnostico
            ''', (usuario_id,))
            historico = cursor.fetchall()
        
        return jsonify([dict(item) for item in historico])
    
    except Exception as e:
        return jsonify({'error': 'Erro ao carregar histórico'}), 500

@app.route('/api/familia')
def api_familia():
    try:
        usuario_id = session.get('usuario_id', 1)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT familia_id FROM usuarios WHERE id = ?', (usuario_id,))
            usuario = cursor.fetchone()
            if usuario and usuario['familia_id']:
                familia_data = obter_dados_familia(cursor, usuario['familia_id'])
                return jsonify(familia_data)
        
        return jsonify({'membros': [], 'media_pontuacao': 0, 'nivel_predominante': 'N/A', 'total_membros': 0})
    
    except Exception as e:
        return jsonify({'error': 'Erro ao carregar dados familiares'}), 500

@app.route('/api/dica-do-dia')
def api_dica_do_dia():
    try:
        usuario_id = session.get('usuario_id', 1)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            dica = obter_dica_do_dia(cursor, usuario_id)
            return jsonify({'dica': dica})
    
    except Exception as e:
        return jsonify({'dica': 'Mantenha o equilíbrio entre vida online e offline!'})

@app.route('/api/cadastrar', methods=['POST'])
def api_cadastrar():
    try:
        data = request.json
        nome = data.get('nome')
        email = data.get('email')
        senha = data.get('senha')
        idade = data.get('idade')
        
        # Validações básicas
        if not nome or not email or not senha or not idade:
            return jsonify({'success': False, 'error': 'Todos os campos são obrigatórios'})
        
        if len(senha) < 6:
            return jsonify({'success': False, 'error': 'A senha deve ter pelo menos 6 caracteres'})
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar se email já existe
            cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
            if cursor.fetchone():
                return jsonify({'success': False, 'error': 'Este email já está cadastrado'})
            
            # Criar nova família para o usuário
            cursor.execute('INSERT INTO familias (nome, codigo_familia) VALUES (?, ?)',
                         (f'Família {nome}', f'FAM{datetime.now().strftime("%Y%m%d%H%M%S")}'))
            familia_id = cursor.lastrowid
            
            # Criar usuário
            cursor.execute('''
                INSERT INTO usuarios (nome, email, idade, familia_id, senha)
                VALUES (?, ?, ?, ?, ?)
            ''', (nome, email, idade, familia_id, senha))
            
            usuario_id = cursor.lastrowid
            conn.commit()
            
            # Configurar sessão
            session['usuario_id'] = usuario_id
            session['usuario_nome'] = nome
            session['usuario_email'] = email
            
            return jsonify({
                'success': True,
                'message': 'Cadastro realizado com sucesso!',
                'usuario_id': usuario_id
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': 'Erro interno do servidor. Tente novamente.'}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.json
        email = data.get('email')
        senha = data.get('senha')
        
        if not email or not senha:
            return jsonify({'success': False, 'error': 'Email e senha são obrigatórios'})
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM usuarios WHERE email = ? AND senha = ?', (email, senha))
            usuario = cursor.fetchone()
            
            if usuario:
                session['usuario_id'] = usuario['id']
                session['usuario_nome'] = usuario['nome']
                session['usuario_email'] = usuario['email']
                
                return jsonify({
                    'success': True,
                    'message': 'Login realizado com sucesso!',
                    'usuario': {
                        'id': usuario['id'],
                        'nome': usuario['nome'],
                        'email': usuario['email']
                    }
                })
            else:
                return jsonify({'success': False, 'error': 'Email ou senha incorretos'})
                
    except Exception as e:
        return jsonify({'success': False, 'error': 'Erro interno do servidor. Tente novamente.'}), 500

@app.route('/api/check-auth')
def api_check_auth():
    try:
        if 'usuario_id' in session:
            return jsonify({
                'authenticated': True, 
                'usuario': {
                    'id': session.get('usuario_id'),
                    'nome': session.get('usuario_nome'),
                    'email': session.get('usuario_email')
                }
            })
        return jsonify({'authenticated': False})
    
    except Exception as e:
        return jsonify({'authenticated': False})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/landing')

# ========== NOVOS ENDPOINTS CORRIGIDOS ==========

@app.route('/api/familia/membros', methods=['POST'])
def api_adicionar_membro_familia():
    try:
        data = request.json
        nome = data.get('nome')
        idade = data.get('idade')
        relacionamento = data.get('relacionamento')
        
        print(f"📥 Recebendo dados para novo membro: {nome}, {idade}, {relacionamento}")
        
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obter familia_id do usuário atual
            cursor.execute('SELECT familia_id FROM usuarios WHERE id = ?', (usuario_id,))
            usuario = cursor.fetchone()
            
            if not usuario or not usuario['familia_id']:
                return jsonify({'success': False, 'error': 'Usuário não pertence a uma família'}), 400
            
            familia_id = usuario['familia_id']
            print(f"🏠 Familia ID encontrada: {familia_id}")
            
            # Inserir novo membro (sem email/senha para membros adicionais)
            cursor.execute('''
                INSERT INTO usuarios (nome, idade, familia_id, relacionamento)
                VALUES (?, ?, ?, ?)
            ''', (nome, idade, familia_id, relacionamento))
            
            novo_membro_id = cursor.lastrowid
            print(f"✅ Novo membro inserido com ID: {novo_membro_id}")
            
            # NÃO criar diagnóstico inicial simulado - o membro deve responder o questionário
            # para ter um diagnóstico real
            
            conn.commit()
            print("💾 Dados commitados com sucesso!")
            
        return jsonify({
            'success': True,
            'message': f'Membro {nome} adicionado com sucesso! O membro deve responder o questionário para obter seu diagnóstico.',
            'membro_id': novo_membro_id
        })
        
    except Exception as e:
        print(f"❌ Erro ao adicionar membro: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/familia/membros/<int:membro_id>', methods=['DELETE'])
def api_excluir_membro_familia(membro_id):
    try:
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar se o membro pertence à mesma família do usuário logado
            cursor.execute('''
                SELECT u1.familia_id as usuario_familia, u2.familia_id as membro_familia, u2.nome
                FROM usuarios u1, usuarios u2 
                WHERE u1.id = ? AND u2.id = ?
            ''', (usuario_id, membro_id))
            resultado = cursor.fetchone()
            
            if not resultado:
                return jsonify({'success': False, 'error': 'Membro não encontrado'}), 404
            
            if resultado['usuario_familia'] != resultado['membro_familia']:
                return jsonify({'success': False, 'error': 'Você não tem permissão para excluir este membro'}), 403
            
            nome_membro = resultado['nome']
            
            # Excluir diagnósticos do membro
            cursor.execute('DELETE FROM diagnosticos WHERE usuario_id = ?', (membro_id,))
            
            # Excluir reflexões do membro
            cursor.execute('DELETE FROM reflexoes WHERE usuario_id = ?', (membro_id,))
            
            # Excluir o membro
            cursor.execute('DELETE FROM usuarios WHERE id = ?', (membro_id,))
            
            conn.commit()
            
        return jsonify({
            'success': True,
            'message': f'Membro {nome_membro} excluído com sucesso!'
        })
        
    except Exception as e:
        print(f"❌ Erro ao excluir membro: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reflexoes', methods=['POST'])
def api_salvar_reflexoes():
    try:
        data = request.json
        reflexoes = data.get('reflexoes', {})
        usuario_id = session.get('usuario_id')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Limpar reflexões anteriores do usuário
            cursor.execute('DELETE FROM reflexoes WHERE usuario_id = ?', (usuario_id,))
            
            # Salvar cada reflexão
            for pergunta, resposta in reflexoes.items():
                if resposta and resposta.strip():  # Só salva se não estiver vazia
                    cursor.execute('''
                        INSERT INTO reflexoes (usuario_id, pergunta, resposta)
                        VALUES (?, ?, ?)
                    ''', (usuario_id, pergunta, resposta))
            
            conn.commit()
            
        return jsonify({'success': True, 'message': 'Reflexões salvas com sucesso!'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reflexoes')
def api_obter_reflexoes():
    """API para obter reflexões salvas do usuário"""
    try:
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return jsonify({'error': 'Não autenticado'}), 401
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pergunta, resposta, data_criacao 
                FROM reflexoes 
                WHERE usuario_id = ? 
                ORDER BY data_criacao DESC
            ''', (usuario_id,))
            reflexoes = cursor.fetchall()
        
        reflexoes_dict = {}
        for reflexao in reflexoes:
            reflexoes_dict[reflexao['pergunta']] = {
                'resposta': reflexao['resposta'],
                'data_criacao': reflexao['data_criacao']
            }
        
        return jsonify({
            'success': True,
            'reflexoes': reflexoes_dict
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/solucoes/<nivel>')
def api_obter_solucoes(nivel):
    try:
        solucoes = ServicoDiagnostico.obter_solucoes_por_nivel(nivel)
        return jsonify({'solucoes': solucoes})
    except Exception as e:
        return jsonify({'solucoes': []})

@app.route('/api/familia/membros/<int:membro_id>')
def api_obter_membro_familia(membro_id):
    try:
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return jsonify({'error': 'Não autenticado'}), 401
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar se o membro pertence à mesma família
            cursor.execute('''
                SELECT u1.familia_id as usuario_familia, u2.familia_id as membro_familia
                FROM usuarios u1, usuarios u2 
                WHERE u1.id = ? AND u2.id = ?
            ''', (usuario_id, membro_id))
            resultado = cursor.fetchone()
            
            if not resultado or resultado['usuario_familia'] != resultado['membro_familia']:
                return jsonify({'error': 'Membro não encontrado ou sem permissão'}), 404
            
            # Obter dados do membro
            cursor.execute('''
                SELECT 
                    u.id, u.nome, u.idade, u.relacionamento,
                    d.pontuacao, d.nivel, d.data_diagnostico
                FROM usuarios u
                LEFT JOIN diagnosticos d ON u.id = d.usuario_id
                WHERE u.id = ?
                ORDER BY d.data_diagnostico DESC
                LIMIT 1
            ''', (membro_id,))
            membro = cursor.fetchone()
            
            if not membro:
                return jsonify({'error': 'Membro não encontrado'}), 404
            
        return jsonify({
            'success': True,
            'membro': dict(membro)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== FUNÇÕES AUXILIARES CORRIGIDAS ==========

def obter_dados_familia(cursor, familia_id):
    if not familia_id:
        return {'membros': [], 'media_pontuacao': 0, 'nivel_predominante': 'N/A', 'total_membros': 0}
    
    try:
        # Query corrigida para pegar o diagnóstico mais recente de cada membro
        cursor.execute('''
            SELECT 
                u.id, 
                u.nome, 
                u.idade, 
                u.relacionamento,
                d.pontuacao, 
                d.nivel, 
                d.data_diagnostico
            FROM usuarios u
            LEFT JOIN (
                SELECT usuario_id, pontuacao, nivel, data_diagnostico,
                       ROW_NUMBER() OVER (PARTITION BY usuario_id ORDER BY data_diagnostico DESC) as rn
                FROM diagnosticos
            ) d ON u.id = d.usuario_id AND d.rn = 1
            WHERE u.familia_id = ?
            ORDER BY d.data_diagnostico DESC
        ''', (familia_id,))
        membros = cursor.fetchall()
        
        if not membros:
            return {'membros': [], 'media_pontuacao': 0, 'nivel_predominante': 'N/A', 'total_membros': 0}
        
        # Converter para dicionário
        membros_dict = []
        for membro in membros:
            membro_dict = dict(membro)
            # Garantir que os campos existam mesmo se forem NULL
            membro_dict['pontuacao'] = membro_dict.get('pontuacao', 0)
            membro_dict['nivel'] = membro_dict.get('nivel', 'Não avaliado')
            membro_dict['relacionamento'] = membro_dict.get('relacionamento', 'Não informado')
            membros_dict.append(membro_dict)
        
        # Calcular estatísticas apenas para membros com diagnóstico
        membros_com_diagnostico = [m for m in membros_dict if m.get('pontuacao') is not None and m['pontuacao'] > 0]
        
        if membros_com_diagnostico:
            pontuacoes = [m['pontuacao'] for m in membros_com_diagnostico]
            media_pontuacao = sum(pontuacoes) / len(pontuacoes)
            
            # Determinar nível predominante
            niveis = [m['nivel'] for m in membros_com_diagnostico if m['nivel'] and m['nivel'] != 'Não avaliado']
            if niveis:
                nivel_predominante = max(set(niveis), key=niveis.count)
            else:
                nivel_predominante = 'N/A'
        else:
            media_pontuacao = 0
            nivel_predominante = 'N/A'
        
        return {
            'membros': membros_dict,
            'media_pontuacao': round(media_pontuacao, 1),
            'nivel_predominante': nivel_predominante,
            'total_membros': len(membros_dict)
        }
    
    except Exception as e:
        print(f"Erro ao obter dados da família: {e}")
        return {'membros': [], 'media_pontuacao': 0, 'nivel_predominante': 'N/A', 'total_membros': 0}

def obter_dica_do_dia(cursor, usuario_id):
    try:
        # Obter último diagnóstico do usuário
        cursor.execute('''
            SELECT nivel FROM diagnosticos 
            WHERE usuario_id = ? 
            ORDER BY data_diagnostico DESC 
            LIMIT 1
        ''', (usuario_id,))
        ultimo_diagnostico = cursor.fetchone()
        
        nivel = ultimo_diagnostico['nivel'] if ultimo_diagnostico else 'Moderado'
        
        dicas = {
            'Dependente': [
                "Que tal definir um alarme para lembrar de fazer pausas a cada hora?",
                "Experimente deixar o celular em outro cômodo durante as refeições",
                "Tente passar a primeira hora do dia sem verificar redes sociais",
                "Estabeleça um horário fixo para desligar todos os dispositivos eletrônicos",
                "Pratique a regra 20-20-20: a cada 20 minutos, olhe por 20 segundos para algo a 20 pés de distância",
                "Desative notificações não essenciais do seu smartphone",
                "Estabeleça metas realistas para reduzir gradualmente o tempo online",
                "Pratique meditação ou exercícios de respiração quando sentir ansiedade"
            ],
            'Moderado': [
                "Parabéns pelo equilíbrio! Continue monitorando seu tempo online",
                "Que tal estabelecer uma 'hora digital' para desligar dispositivos?",
                "Pratique atividades sem telas antes de dormir para melhorar a qualidade do sono",
                "Experimente ter um dia por semana com uso mínimo de internet",
                "Mantenha um diário das atividades offline que mais lhe dão prazer",
                "Estabeleça zonas livres de tecnologia em sua casa",
                "Pratique a técnica Pomodoro (25 minutos focado, 5 minutos de pausa)",
                "Desenvolva um hobby que não envolva telas"
            ],
            'Não dependente': [
                "Excelente trabalho mantendo hábitos saudáveis!",
                "Compartilhe suas estratégias de equilíbrio digital com amigos e familiares",
                "Continue aproveitando o melhor da tecnologia sem excessos",
                "Ajude outros membros da família a encontrar o equilíbrio",
                "Periodicamente reavalie seu relacionamento com a tecnologia",
                "Mantenha atividades sociais presenciais regularmente",
                "Continue com exercícios físicos e hobbies offline",
                "Comemore suas conquistas de equilíbrio digital"
            ]
        }
        
        dicas_nivel = dicas.get(nivel, dicas['Moderado'])
        
        # Usar o dia do ano para escolher uma dica consistentemente
        dia_do_ano = datetime.now().timetuple().tm_yday
        return dicas_nivel[dia_do_ano % len(dicas_nivel)]
    
    except Exception as e:
        return "Mantenha o equilíbrio entre vida online e offline!"

# ========== MANUTENÇÃO DO BANCO ==========

@app.route('/reset-db')
def reset_database():
    """Rota para resetar o banco de dados (apenas para desenvolvimento)"""
    try:
        if os.path.exists('neteNDENCIA.db'):
            os.remove('neteNDENCIA.db')
            print("🗑️ Banco de dados antigo removido")
        
        init_database()
        inserir_perguntas_iniciais()
        atualizar_schema()
        return jsonify({'success': True, 'message': 'Banco de dados resetado com sucesso!'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/debug-tables')
def debug_tables():
    """Rota para debug da estrutura das tabelas"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Verificar estrutura da tabela usuarios
        cursor.execute("PRAGMA table_info(usuarios)")
        colunas_usuarios = cursor.fetchall()
        
        # Verificar dados atuais
        cursor.execute("SELECT * FROM usuarios")
        usuarios = cursor.fetchall()
        
        return jsonify({
            'colunas_usuarios': [dict(coluna) for coluna in colunas_usuarios],
            'usuarios': [dict(usuario) for usuario in usuarios]
        })

# ========== INICIALIZAÇÃO ==========

if __name__ == '__main__':
    print("🚀 Inicializando NETENDENCIA...")
    
    # Verificar se a pasta templates existe
    if not os.path.exists('templates'):
        os.makedirs('templates')
        print("📁 Pasta templates criada")
    
    init_database()
    inserir_perguntas_iniciais()
    atualizar_schema()  # 👈 ADICIONADO: Atualiza o schema do banco
    print("✅ Sistema inicializado com sucesso!")
    print("🌐 Acesse: http://localhost:5000/landing")
    print("📊 Dashboard: http://localhost:5000/ (após login)")
    print("🔄 Para resetar o BD: http://localhost:5000/reset-db")
    print("🐛 Para debug: http://localhost:5000/debug-tables")
    
    app.run(debug=True, host='0.0.0.0', port=5000)