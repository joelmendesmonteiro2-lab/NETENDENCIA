from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
import json
import random
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from contextlib import contextmanager

app = Flask(__name__)
app.secret_key = 'neteNDENCIA_secret_key_2025'
app.config['TEMPLATES_AUTO_RELOAD'] = True

# ========== CONFIGURAÇÃO DO BANCO DE DADOS POSTGRESQL AWS ==========

@contextmanager
def get_db_connection():
    conn = psycopg2.connect(
        host='netendencia.c09gmwigavdx.us-east-1.rds.amazonaws.com',
        database='dbnetendencia',
        user='postgres',
        password='netendencia1',
        port='5432',
        connect_timeout=10
    )
    conn.cursor_factory = RealDictCursor
    try:
        yield conn
    except Exception as e:
        print(f"❌ Erro na conexão PostgreSQL: {e}")
        raise
    finally:
        conn.close()

def init_database():
    """Verifica a conexão com o PostgreSQL"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tabela_count = cursor.fetchone()['count']
            
            print(f"✅ Conectado ao PostgreSQL AWS! {tabela_count} tabelas encontradas.")
            
    except Exception as e:
        print(f"❌ Erro ao conectar com PostgreSQL AWS: {e}")

# ========== FUNÇÕES AUXILIARES CORRIGIDAS ==========

def obter_dados_familia(cursor, familia_id):
    """CORRIGIDA - Obter dados da família com tratamento robusto"""
    if not familia_id:
        return {
            'membros': [], 
            'media_pontuacao': 0, 
            'nivel_predominante': 'N/A', 
            'total_membros': 0,
            'status': 'sem_familia'
        }
    
    try:
        # Query mais simples e eficiente
        cursor.execute('''
            SELECT 
                u.id, 
                u.nome, 
                u.idade, 
                u.relacionamento,
                (SELECT pontuacao FROM diagnosticos 
                 WHERE usuario_id = u.id 
                 ORDER BY data_diagnostico DESC 
                 LIMIT 1) as pontuacao,
                (SELECT nivel FROM diagnosticos 
                 WHERE usuario_id = u.id 
                 ORDER BY data_diagnostico DESC 
                 LIMIT 1) as nivel
            FROM usuarios u
            WHERE u.familia_id = %s
            ORDER BY u.id
        ''', (familia_id,))
        
        membros = cursor.fetchall()
        
        if not membros:
            return {
                'membros': [], 
                'media_pontuacao': 0, 
                'nivel_predominante': 'N/A', 
                'total_membros': 0,
                'status': 'sem_membros'
            }
        
        # Processar membros
        membros_processados = []
        pontuacoes_validas = []
        niveis_validos = []
        
        for membro in membros:
            membro_dict = dict(membro)
            
            # Garantir valores padrão
            pontuacao = membro_dict.get('pontuacao')
            nivel = membro_dict.get('nivel')
            
            membro_dict['pontuacao'] = pontuacao if pontuacao is not None else 0
            membro_dict['nivel'] = nivel if nivel else 'Não avaliado'
            membro_dict['relacionamento'] = membro_dict.get('relacionamento') or 'Não informado'
            membro_dict['tem_diagnostico'] = pontuacao is not None
            
            membros_processados.append(membro_dict)
            
            # Coletar dados para estatísticas apenas de membros com diagnóstico
            if pontuacao is not None and pontuacao > 0:
                pontuacoes_validas.append(pontuacao)
            if nivel and nivel != 'Não avaliado':
                niveis_validos.append(nivel)
        
        # Calcular estatísticas
        media_pontuacao = 0
        if pontuacoes_validas:
            media_pontuacao = sum(pontuacoes_validas) / len(pontuacoes_validas)
        
        nivel_predominante = 'N/A'
        if niveis_validos:
            # Encontrar nível mais comum
            contador_niveis = {}
            for nivel in niveis_validos:
                contador_niveis[nivel] = contador_niveis.get(nivel, 0) + 1
            
            nivel_predominante = max(contador_niveis, key=contador_niveis.get)
        
        print(f"👨‍👩‍👧‍👦 Panorama familiar: {len(membros_processados)} membros, Média: {media_pontuacao:.1f}, Nível: {nivel_predominante}")
        
        return {
            'membros': membros_processados,
            'media_pontuacao': round(media_pontuacao, 1),
            'nivel_predominante': nivel_predominante,
            'total_membros': len(membros_processados),
            'membros_com_diagnostico': len(pontuacoes_validas),
            'status': 'sucesso'
        }
    
    except Exception as e:
        print(f"❌ Erro ao obter dados da família: {e}")
        return {
            'membros': [], 
            'media_pontuacao': 0, 
            'nivel_predominante': 'N/A', 
            'total_membros': 0,
            'status': 'erro',
            'erro': str(e)
        }

def obter_dica_do_dia(cursor, usuario_id):
    """CORRIGIDA - Obter dica do dia com verificação robusta"""
    try:
        nivel = 'Moderado'  # Valor padrão
        
        if usuario_id:
            cursor.execute('''
                SELECT nivel FROM diagnosticos 
                WHERE usuario_id = %s 
                ORDER BY data_diagnostico DESC 
                LIMIT 1
            ''', (usuario_id,))
            ultimo_diagnostico = cursor.fetchone()
            
            if ultimo_diagnostico and ultimo_diagnostico.get('nivel'):
                nivel = ultimo_diagnostico['nivel']
        
        print(f"🎯 Dica do dia - Usuário {usuario_id}, Nível: {nivel}")
        
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
        
        # Garantir que o nível existe, caso contrário usar Moderado
        dicas_nivel = dicas.get(nivel, dicas['Moderado'])
        
        # Escolher dica baseada no dia do ano (sempre muda)
        dia_do_ano = datetime.now().timetuple().tm_yday
        indice_dica = dia_do_ano % len(dicas_nivel)
        dica_escolhida = dicas_nivel[indice_dica]
        
        print(f"💡 Dica escolhida: {dica_escolhida} (índice: {indice_dica})")
        return dica_escolhida
    
    except Exception as e:
        print(f"❌ Erro ao obter dica do dia: {e}")
        return "Mantenha o equilíbrio entre vida online e offline! Pratique atividades offline regularmente."

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
        """Verifica se é necessário fazer reavaliação"""
        if not ultimo_diagnostico:
            return True
        
        try:
            if isinstance(ultimo_diagnostico['data_diagnostico'], str):
                try:
                    data_ultimo = datetime.fromisoformat(ultimo_diagnostico['data_diagnostico'].replace('Z', '+00:00'))
                except:
                    data_ultimo = datetime.strptime(ultimo_diagnostico['data_diagnostico'], '%Y-%m-%d %H:%M:%S')
            else:
                data_ultimo = ultimo_diagnostico['data_diagnostico']
                
            return (datetime.now() - data_ultimo).days >= 30
        except:
            return True

# ========== ROTAS PRINCIPAIS ==========

@app.route('/')
def index():
    if 'usuario_id' not in session:
        return redirect('/landing')
    return render_template('index.html')

@app.route('/landing')
def landing():
    return render_template('landing.html')

@app.route('/avaliacao-geral')
def avaliacao_geral():
    """Rota para a página de avaliação geral - ACESSO PÚBLICO"""
    return render_template('avaliacao-geral.html')

@app.route('/instituicoes')
def pagina_instituicoes():
    if 'usuario_id' not in session:
        return redirect('/landing')
    return render_template('instituicoes.html')

@app.route('/cadastrar-instituicao')
def pagina_cadastrar_instituicao():
    return render_template('cadastrar_instituicao.html')

@app.route('/cadastrar-profissional')
def pagina_cadastrar_profissional():
    return render_template('cadastrar_profissional.html')

@app.route('/lista-instituicoes')
def pagina_lista_instituicoes():
    return render_template('lista_instituicoes.html')

# ========== API CORRIGIDA PARA AVALIAÇÃO GERAL ==========

@app.route('/api/avaliacao-geral/dados')
def api_avaliacao_geral_dados():
    """API para obter dados da avaliação geral - TODOS OS USUÁRIOS DO SISTEMA"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Buscar TODOS os usuários do sistema
            cursor.execute('''
                SELECT 
                    u.id,
                    u.nome,
                    u.relacionamento,
                    u.familia_id,
                    (SELECT pontuacao FROM diagnosticos 
                     WHERE usuario_id = u.id 
                     ORDER BY data_diagnostico DESC 
                     LIMIT 1) as pontuacao,
                    (SELECT nivel FROM diagnosticos 
                     WHERE usuario_id = u.id 
                     ORDER BY data_diagnostico DESC 
                     LIMIT 1) as nivel,
                    (SELECT data_diagnostico FROM diagnosticos 
                     WHERE usuario_id = u.id 
                     ORDER BY data_diagnostico DESC 
                     LIMIT 1) as data_diagnostico
                FROM usuarios u
                ORDER BY u.familia_id, u.nome
            ''')
            
            todos_usuarios = cursor.fetchall()
            
            # Processar dados para estatísticas
            total_usuarios = len(todos_usuarios)
            usuarios_avaliados = 0
            pontuacoes_validas = []
            contador_niveis = {
                'Não dependente': 0,
                'Moderado': 0,
                'Dependente': 0,
                'Não avaliado': 0
            }
            
            detalhes = []
            
            for usuario in todos_usuarios:
                usuario_dict = dict(usuario)
                nivel = usuario_dict['nivel'] if usuario_dict['nivel'] else 'Não avaliado'
                pontuacao = usuario_dict['pontuacao'] if usuario_dict['pontuacao'] is not None else None
                
                # Marcar se é o usuário logado (se houver)
                usuario_logado_id = session.get('usuario_id')
                is_usuario_logado = usuario_logado_id and usuario_dict['id'] == usuario_logado_id
                categoria = 'Você' if is_usuario_logado else usuario_dict.get('relacionamento', 'Usuário')
                
                # Adicionar família ao nome para identificação
                nome_com_familia = f"{usuario_dict['nome']} (Família {usuario_dict['familia_id']})"
                
                # Contar usuários avaliados
                if pontuacao is not None:
                    usuarios_avaliados += 1
                    pontuacoes_validas.append(pontuacao)
                
                # Contar níveis
                contador_niveis[nivel] = contador_niveis.get(nivel, 0) + 1
                
                # Adicionar aos detalhes
                detalhes.append({
                    'nome': nome_com_familia,
                    'categoria': categoria,
                    'pontuacao': pontuacao,
                    'nivel': nivel,
                    'data_diagnostico': usuario_dict['data_diagnostico'],
                    'is_usuario_logado': is_usuario_logado
                })
            
            # Calcular estatísticas
            percentual_avaliados = 0
            if total_usuarios > 0:
                percentual_avaliados = round((usuarios_avaliados / total_usuarios) * 100, 1)
            
            media_geral = 0
            if pontuacoes_validas:
                media_geral = round(sum(pontuacoes_validas) / len(pontuacoes_validas), 1)
            
            # Encontrar nível mais comum (excluindo "Não avaliado")
            niveis_avaliados = {k: v for k, v in contador_niveis.items() if k != 'Não avaliado' and v > 0}
            nivel_mais_comum = 'N/A'
            if niveis_avaliados:
                nivel_mais_comum = max(niveis_avaliados, key=niveis_avaliados.get)
            
            # Preparar dados para o gráfico de pizza
            dados_grafico = []
            cores = {
                'Não dependente': '#28a745',  # Verde
                'Moderado': '#ffc107',        # Amarelo 
                'Dependente': '#dc3545',      # Vermelho
                'Não avaliado': '#6c757d'     # Cinza
            }
            
            for nivel, quantidade in contador_niveis.items():
                if quantidade > 0:
                    percentual = round((quantidade / total_usuarios) * 100, 1) if total_usuarios > 0 else 0
                    dados_grafico.append({
                        'nivel': nivel,
                        'quantidade': quantidade,
                        'percentual': percentual,
                        'cor': cores.get(nivel, '#6c757d')
                    })
            
            # Ordenar dados do gráfico por quantidade (decrescente)
            dados_grafico.sort(key=lambda x: x['quantidade'], reverse=True)
            
            print(f"📊 Avaliação Geral: {total_usuarios} usuários, {usuarios_avaliados} avaliados, Média: {media_geral}")
            
            return jsonify({
                'success': True,
                'estatisticas': {
                    'total_usuarios': total_usuarios,
                    'total_avaliados': usuarios_avaliados,
                    'percentual_avaliados': percentual_avaliados,
                    'media_geral': media_geral,
                    'nivel_mais_comum': nivel_mais_comum,
                    'descricao': 'Dados de todos os usuários do sistema'
                },
                'dados_grafico': {
                    'niveis': dados_grafico
                },
                'detalhes': detalhes,
                'usuario_logado_id': session.get('usuario_id'),
                'modo_demo': False
            })
            
    except Exception as e:
        print(f"❌ Erro ao obter dados da avaliação geral: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== APIs CORRIGIDAS ==========

@app.route('/api/dashboard-data')
def api_dashboard_data():
    """CORRIGIDA - API para dados do dashboard com melhor tratamento"""
    if 'usuario_id' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    
    usuario_id = session.get('usuario_id')
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Dados do usuário
            cursor.execute('SELECT * FROM usuarios WHERE id = %s', (usuario_id,))
            usuario_result = cursor.fetchone()
            
            if not usuario_result:
                return jsonify({'error': 'Usuário não encontrado'}), 404
            
            usuario = dict(usuario_result)
            print(f"👤 Dashboard - Usuário: {usuario['nome']}, Família: {usuario.get('familia_id')}")
            
            # Último diagnóstico
            cursor.execute('''
                SELECT * FROM diagnosticos 
                WHERE usuario_id = %s 
                ORDER BY data_diagnostico DESC 
                LIMIT 1
            ''', (usuario_id,))
            ultimo_diagnostico_result = cursor.fetchone()
            ultimo_diagnostico = dict(ultimo_diagnostico_result) if ultimo_diagnostico_result else None
            
            # Histórico para gráfico
            cursor.execute('''
                SELECT pontuacao, nivel, data_diagnostico 
                FROM diagnosticos 
                WHERE usuario_id = %s 
                ORDER BY data_diagnostico
            ''', (usuario_id,))
            historico_results = cursor.fetchall()
            historico = [dict(item) for item in historico_results]
            
            # Dados da família - AGORA CORRIGIDO
            familia_data = obter_dados_familia(cursor, usuario.get('familia_id'))
            
            # Dica do dia - AGORA CORRIGIDO
            dica_do_dia = obter_dica_do_dia(cursor, usuario_id)
            
            # Verificar necessidade de reavaliação
            precisa_reavaliar = False
            if ultimo_diagnostico:
                precisa_reavaliar = ServicoDiagnostico.verificar_reavaliacao_necesaria(ultimo_diagnostico)
        
        return jsonify({
            'success': True,
            'usuario': usuario,
            'ultimo_diagnostico': ultimo_diagnostico,
            'historico': historico,
            'familia_data': familia_data,
            'dica_do_dia': dica_do_dia,
            'precisa_reavaliar': precisa_reavaliar
        })
        
    except Exception as e:
        print(f"❌ Erro no dashboard-data: {e}")
        return jsonify({
            'success': False, 
            'error': 'Erro ao carregar dados do dashboard',
            'dica_do_dia': 'Mantenha o equilíbrio entre vida online e offline!'
        }), 500

# ========== APIs FALTANTES QUE ESTAVAM COM ERRO 404 ==========

@app.route('/api/familia', methods=['GET'])
def api_obter_familia():
    """API para obter dados da família - ESTAVA FALTANDO"""
    try:
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return jsonify({'error': 'Não autenticado'}), 401
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obter familia_id do usuário
            cursor.execute('SELECT familia_id FROM usuarios WHERE id = %s', (usuario_id,))
            usuario_result = cursor.fetchone()
            
            if not usuario_result or not usuario_result['familia_id']:
                return jsonify({'success': False, 'error': 'Usuário não pertence a uma família'}), 400
            
            familia_id = usuario_result['familia_id']
            familia_data = obter_dados_familia(cursor, familia_id)
            
        return jsonify({
            'success': True,
            'familia': familia_data
        })
        
    except Exception as e:
        print(f"❌ Erro ao obter dados da família: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/solucoes/<nivel>', methods=['GET'])
def api_obter_solucoes(nivel):
    """API para obter soluções por nível - ESTAVA FALTANDO"""
    try:
        solucoes = ServicoDiagnostico.obter_solucoes_por_nivel(nivel)
        return jsonify({
            'success': True,
            'nivel': nivel,
            'solucoes': solucoes
        })
    except Exception as e:
        print(f"❌ Erro ao obter soluções: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/plano-acao', methods=['GET', 'POST'])
def api_plano_acao():
    """API para plano de ação - ESTAVA FALTANDO"""
    try:
        if request.method == 'GET':
            # Retornar plano de ação existente ou vazio
            usuario_id = session.get('usuario_id')
            if not usuario_id:
                return jsonify({'error': 'Não autenticado'}), 401
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT plano_acao FROM usuarios WHERE id = %s
                ''', (usuario_id,))
                resultado = cursor.fetchone()
                
                plano_acao = resultado['plano_acao'] if resultado and resultado['plano_acao'] else {}
                
            return jsonify({
                'success': True,
                'plano_acao': plano_acao
            })
            
        elif request.method == 'POST':
            # Salvar plano de ação
            data = request.json
            plano_acao = data.get('plano_acao', {})
            usuario_id = session.get('usuario_id')
            
            if not usuario_id:
                return jsonify({'error': 'Não autenticado'}), 401
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE usuarios SET plano_acao = %s WHERE id = %s
                ''', (json.dumps(plano_acao), usuario_id))
                conn.commit()
                
            return jsonify({
                'success': True,
                'message': 'Plano de ação salvo com sucesso!'
            })
            
    except Exception as e:
        print(f"❌ Erro no plano de ação: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== APIs PARA INSTITUIÇÕES E PROFISSIONAIS ==========

@app.route('/api/instituicoes', methods=['GET'])
def api_obter_instituicoes():
    """API para obter instituições cadastradas"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM instituicoes 
                ORDER BY nome
            ''')
            instituicoes = cursor.fetchall()
            
        return jsonify({
            'success': True,
            'instituicoes': [dict(inst) for inst in instituicoes]
        })
        
    except Exception as e:
        print(f"❌ Erro ao obter instituições: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/instituicoes/cadastrar', methods=['POST'])
def api_cadastrar_instituicao():
    """API para cadastrar nova instituição"""
    try:
        data = request.json
        nome = data.get('nome')
        tipo = data.get('tipo')
        endereco = data.get('endereco')
        telefone = data.get('telefone')
        email = data.get('email')
        descricao = data.get('descricao')
        especialidades = data.get('especialidades')
        
        print(f"📥 Recebendo requisição para cadastrar instituição...")
        print(f"📊 Dados recebidos: {data}")
        
        # Validações básicas
        if not nome or not tipo:
            return jsonify({'success': False, 'error': 'Nome e tipo são obrigatórios'}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO instituicoes (nome, tipo, endereco, telefone, email, descricao, especialidades)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
            ''', (nome, tipo, endereco, telefone, email, descricao, especialidades))
            
            instituicao_id = cursor.fetchone()['id']
            conn.commit()
            
            print(f"✅ Instituição cadastrada com ID: {instituicao_id}")
            
        return jsonify({
            'success': True,
            'message': 'Instituição cadastrada com sucesso!',
            'instituicao_id': instituicao_id
        })
        
    except Exception as e:
        print(f"❌ Erro ao cadastrar instituição: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/profissionais', methods=['GET'])
def api_obter_profissionais():
    """API para obter profissionais cadastrados"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM profissionais 
                ORDER BY nome
            ''')
            profissionais = cursor.fetchall()
            
        return jsonify({
            'success': True,
            'profissionais': [dict(prof) for prof in profissionais]
        })
        
    except Exception as e:
        print(f"❌ Erro ao obter profissionais: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/profissionais/cadastrar', methods=['POST'])
def api_cadastrar_profissional():
    """API CORRIGIDA - Para cadastrar novo profissional"""
    try:
        data = request.json
        nome = data.get('nome')
        profissao = data.get('profissao')
        especialidade = data.get('especialidade')
        telefone = data.get('telefone')
        email = data.get('email')
        instituicao_id = data.get('instituicao_id')  # CORREÇÃO: instituicao → instituicao_id
        registro_profissional = data.get('registro_profissional', '')
        abordagem = data.get('abordagem', '')
        descricao = data.get('descricao')
        
        print(f"📥 Recebendo requisição para cadastrar profissional...")
        print(f"📊 Dados recebidos: {data}")
        
        # Validações básicas
        if not nome:
            return jsonify({'success': False, 'error': 'Nome é obrigatório'}), 400
        
        if not especialidade:
            return jsonify({'success': False, 'error': 'Especialidade é obrigatória'}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar se já existe um profissional com o mesmo email
            if email:
                cursor.execute('SELECT id FROM profissionais WHERE email = %s', (email,))
                if cursor.fetchone():
                    return jsonify({'success': False, 'error': 'Já existe um profissional com este email'}), 400
            
            # CORREÇÃO: Query com nomes de colunas corretos
            cursor.execute('''
                INSERT INTO profissionais 
                (nome, profissao, especialidade, telefone, email, instituicao_id, 
                 registro_profissional, abordagem, descricao, data_cadastro)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP) 
                RETURNING id
            ''', (nome, profissao, especialidade, telefone, email, instituicao_id,
                 registro_profissional, abordagem, descricao))
            
            resultado = cursor.fetchone()
            if resultado:
                profissional_id = resultado['id']
            else:
                return jsonify({'success': False, 'error': 'Erro ao obter ID do profissional'}), 500
                
            conn.commit()
            
            print(f"✅ Profissional cadastrado com ID: {profissional_id}")
            
        return jsonify({
            'success': True,
            'message': 'Profissional cadastrado com sucesso!',
            'profissional_id': profissional_id
        })
        
    except Exception as e:
        print(f"❌ Erro ao cadastrar profissional: {e}")
        return jsonify({'success': False, 'error': f'Erro interno do servidor: {str(e)}'}), 500

@app.route('/api/instituicoes/<int:instituicao_id>', methods=['DELETE'])
def api_excluir_instituicao(instituicao_id):
    """API para excluir instituição"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM instituicoes WHERE id = %s', (instituicao_id,))
            conn.commit()
            
            print(f"✅ Instituição {instituicao_id} excluída com sucesso!")
            
        return jsonify({
            'success': True,
            'message': 'Instituição excluída com sucesso!'
        })
        
    except Exception as e:
        print(f"❌ Erro ao excluir instituição: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/profissionais/<int:profissional_id>', methods=['DELETE'])
def api_excluir_profissional(profissional_id):
    """API para excluir profissional"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM profissionais WHERE id = %s', (profissional_id,))
            conn.commit()
            
            print(f"✅ Profissional {profissional_id} excluído com sucesso!")
            
        return jsonify({
            'success': True,
            'message': 'Profissional excluído com sucesso!'
        })
        
    except Exception as e:
        print(f"❌ Erro ao excluir profissional: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== NOVA ROTA PARA INSTITUIÇÕES COM PROFISSIONAIS ==========

@app.route('/api/instituicoes-com-profissionais', methods=['GET'])
def api_obter_instituicoes_com_profissionais():
    """API para obter instituições com seus profissionais"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Buscar instituições
            cursor.execute('''
                SELECT * FROM instituicoes 
                ORDER BY nome
            ''')
            instituicoes = cursor.fetchall()
            
            # Para cada instituição, buscar seus profissionais
            instituicoes_com_profissionais = []
            for instituicao in instituicoes:
                instituicao_dict = dict(instituicao)
                
                cursor.execute('''
                    SELECT * FROM profissionais 
                    WHERE instituicao_id = %s 
                    ORDER BY nome
                ''', (instituicao['id'],))
                
                profissionais = cursor.fetchall()
                instituicao_dict['profissionais'] = [dict(prof) for prof in profissionais]
                instituicoes_com_profissionais.append(instituicao_dict)
            
            print(f"✅ Instituições com profissionais carregadas: {len(instituicoes_com_profissionais)} instituições")
            
        return jsonify({
            'success': True,
            'instituicoes': instituicoes_com_profissionais
        })
        
    except Exception as e:
        print(f"❌ Erro ao obter instituições com profissionais: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== APIs EXISTENTES CORRIGIDAS ==========

@app.route('/api/familia/membros', methods=['POST'])
def api_adicionar_membro_familia():
    """CORRIGIDA - API para adicionar membro da família"""
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
            cursor.execute('SELECT familia_id FROM usuarios WHERE id = %s', (usuario_id,))
            usuario_result = cursor.fetchone()
            
            if not usuario_result or not usuario_result['familia_id']:
                return jsonify({'success': False, 'error': 'Usuário não pertence a uma família'}), 400
            
            familia_id = usuario_result['familia_id']
            print(f"🏠 Familia ID encontrada: {familia_id}")
            
            # Inserir novo membro
            cursor.execute('''
                INSERT INTO usuarios (nome, idade, familia_id, relacionamento)
                VALUES (%s, %s, %s, %s) RETURNING id
            ''', (nome, idade, familia_id, relacionamento))
            
            novo_membro_id = cursor.fetchone()['id']
            conn.commit()
            
            print(f"✅ Novo membro inserido com ID: {novo_membro_id}")
            
        return jsonify({
            'success': True,
            'message': f'Membro {nome} adicionado com sucesso!',
            'membro_id': novo_membro_id
        })
        
    except Exception as e:
        print(f"❌ Erro ao adicionar membro: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/familia/membros/<int:membro_id>', methods=['DELETE'])
def api_excluir_membro_familia(membro_id):
    """CORRIGIDA - API para excluir membro da família"""
    try:
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar se o membro pertence à mesma família
            cursor.execute('''
                SELECT u1.familia_id as usuario_familia, u2.familia_id as membro_familia, u2.nome
                FROM usuarios u1, usuarios u2 
                WHERE u1.id = %s AND u2.id = %s
            ''', (usuario_id, membro_id))
            resultado = cursor.fetchone()
            
            if not resultado:
                return jsonify({'success': False, 'error': 'Membro não encontrado'}), 404
            
            if resultado['usuario_familia'] != resultado['membro_familia']:
                return jsonify({'success': False, 'error': 'Você não tem permissão para excluir este membro'}), 403
            
            nome_membro = resultado['nome']
            
            # Excluir diagnósticos do membro
            cursor.execute('DELETE FROM diagnosticos WHERE usuario_id = %s', (membro_id,))
            
            # Excluir reflexões do membro
            cursor.execute('DELETE FROM reflexoes WHERE usuario_id = %s', (membro_id,))
            
            # Excluir o membro
            cursor.execute('DELETE FROM usuarios WHERE id = %s', (membro_id,))
            
            conn.commit()
            
            print(f"✅ Membro {nome_membro} excluído com sucesso!")
            
        return jsonify({
            'success': True,
            'message': f'Membro {nome_membro} excluído com sucesso!'
        })
        
    except Exception as e:
        print(f"❌ Erro ao excluir membro: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/familia/membros/<int:membro_id>/diagnostico', methods=['POST'])
def api_salvar_diagnostico_familiar(membro_id):
    """CORRIGIDA - API para salvar diagnóstico de membro da família"""
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
                WHERE u1.id = %s AND u2.id = %s
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
                VALUES (%s, %s, %s, %s) RETURNING id
            ''', (membro_id, pontuacao_total, nivel, json.dumps(respostas)))
            
            diagnostico_id = cursor.fetchone()['id']
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
        print(f"❌ Erro ao salvar diagnóstico familiar: {e}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@app.route('/api/reflexoes', methods=['GET', 'POST'])
def api_reflexoes():
    """API unificada para reflexões"""
    try:
        if request.method == 'GET':
            usuario_id = session.get('usuario_id')
            if not usuario_id:
                return jsonify({'error': 'Não autenticado'}), 401
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT pergunta, resposta, data_criacao 
                    FROM reflexoes 
                    WHERE usuario_id = %s 
                    ORDER BY data_criacao DESC
                ''', (usuario_id,))
                reflexoes = cursor.fetchall()
            
            reflexoes_dict = {}
            for reflexao in reflexoes:
                reflexoes_dict[reflexao['pergunta']] = {
                    'resposta': reflexao['resposta'],
                    'data_criacao': reflexao['data_criacao']
                }
            
            print(f"📖 Carregadas {len(reflexoes_dict)} reflexões para usuário {usuario_id}")
            
            return jsonify({
                'success': True,
                'reflexoes': reflexoes_dict
            })
            
        elif request.method == 'POST':
            data = request.json
            reflexoes = data.get('reflexoes', {})
            usuario_id = session.get('usuario_id')
            
            if not usuario_id:
                return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401
            
            print(f"💭 Salvando reflexões para usuário {usuario_id}: {len(reflexoes)} respostas")
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Limpar reflexões anteriores do usuário
                cursor.execute('DELETE FROM reflexoes WHERE usuario_id = %s', (usuario_id,))
                
                # Salvar cada reflexão
                for pergunta, resposta in reflexoes.items():
                    if resposta and resposta.strip():  # Só salva se não estiver vazia
                        cursor.execute('''
                            INSERT INTO reflexoes (usuario_id, pergunta, resposta)
                            VALUES (%s, %s, %s)
                        ''', (usuario_id, pergunta, resposta))
                        print(f"✅ Reflexão salva: {pergunta} -> {resposta}")
                
                conn.commit()
                print("💾 Todas as reflexões salvas com sucesso!")
                
            return jsonify({'success': True, 'message': 'Reflexões salvas com sucesso!'})
            
    except Exception as e:
        print(f"❌ Erro nas reflexões: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dica-do-dia')
def api_dica_do_dia():
    """CORRIGIDA - API para obter dica do dia"""
    try:
        usuario_id = session.get('usuario_id', 1)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            dica = obter_dica_do_dia(cursor, usuario_id)
            return jsonify({'dica': dica})
    
    except Exception as e:
        print(f"❌ Erro em /api/dica-do-dia: {e}")
        return jsonify({'dica': 'Mantenha o equilíbrio entre vida online e offline!'})

# ========== APIs EXISTENTES (mantenha as que já estão funcionando) ==========

@app.route('/api/perguntas')
def api_perguntas():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.id, p.texto, p.categoria,
                       json_agg(json_build_object('id', o.id, 'texto', o.texto, 'pontuacao', o.pontuacao)) as opcoes
                FROM perguntas p
                LEFT JOIN opcoes_resposta o ON p.id = o.pergunta_id
                GROUP BY p.id, p.texto, p.categoria
                ORDER BY p.id
            ''')
            perguntas = cursor.fetchall()
        
        perguntas_formatadas = []
        for pergunta in perguntas:
            opcoes = pergunta['opcoes'] if pergunta['opcoes'] else []
            opcoes = [opcao for opcao in opcoes if opcao['id'] is not None]
                
            perguntas_formatadas.append({
                'id': pergunta['id'],
                'texto': pergunta['texto'],
                'categoria': pergunta['categoria'],
                'opcoes': opcoes
            })
        
        return jsonify(perguntas_formatadas)
    
    except Exception as e:
        print(f"❌ Erro em /api/perguntas: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/diagnostico', methods=['POST'])
def api_salvar_diagnostico():
    try:
        data = request.json
        respostas = data.get('respostas', [])
        usuario_id = session.get('usuario_id')
        
        if not usuario_id:
            return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401
        
        pontuacao_total = sum(resposta['pontuacao'] for resposta in respostas)
        nivel = ServicoDiagnostico.calcular_nivel(pontuacao_total)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO diagnosticos (usuario_id, pontuacao, nivel, respostas)
                VALUES (%s, %s, %s, %s) RETURNING id
            ''', (usuario_id, pontuacao_total, nivel, json.dumps(respostas)))
            
            diagnostico_id = cursor.fetchone()['id']
            conn.commit()
        
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
        print(f"❌ Erro em /api/diagnostico: {e}")
        return jsonify({'success': False, 'error': 'Erro interno do servidor'}), 500

@app.route('/api/cadastrar', methods=['POST'])
def api_cadastrar():
    try:
        data = request.json
        nome = data.get('nome')
        email = data.get('email')
        senha = data.get('senha')
        idade = data.get('idade')
        
        if not nome or not email or not senha or not idade:
            return jsonify({'success': False, 'error': 'Todos os campos são obrigatórios'})
        
        if len(senha) < 6:
            return jsonify({'success': False, 'error': 'A senha deve ter pelo menos 6 caracteres'})
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM usuarios WHERE email = %s', (email,))
            if cursor.fetchone():
                return jsonify({'success': False, 'error': 'Este email já está cadastrado'})
            
            cursor.execute('INSERT INTO familias (nome, codigo_familia) VALUES (%s, %s) RETURNING id',
                         (f'Família {nome}', f'FAM{datetime.now().strftime("%Y%m%d%H%M%S")}'))
            familia_id = cursor.fetchone()['id']
            
            cursor.execute('''
                INSERT INTO usuarios (nome, email, idade, familia_id, senha)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            ''', (nome, email, idade, familia_id, senha))
            
            usuario_id = cursor.fetchone()['id']
            conn.commit()
            
            session['usuario_id'] = usuario_id
            session['usuario_nome'] = nome
            session['usuario_email'] = email
            
            return jsonify({
                'success': True,
                'message': 'Cadastro realizado com sucesso!',
                'usuario_id': usuario_id
            })
            
    except Exception as e:
        print(f"❌ Erro em /api/cadastrar: {e}")
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
            cursor.execute('SELECT * FROM usuarios WHERE email = %s AND senha = %s', (email, senha))
            usuario = cursor.fetchone()
            
            if usuario:
                session['usuario_id'] = usuario['id']
                session['usuario_nome'] = usuario['nome']
                session['usuario_email'] = usuario['email']
                
                print(f"✅ Login realizado: {usuario['nome']}")
                
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
        print(f"❌ Erro em /api/login: {e}")
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

# ========== ROTAS DE DEBUG ==========

@app.route('/debug-reflexoes')
def debug_reflexoes():
    """Debug das reflexões no banco"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT r.*, u.nome as usuario_nome 
                FROM reflexoes r
                JOIN usuarios u ON r.usuario_id = u.id
                ORDER BY r.data_criacao DESC
            ''')
            reflexoes = cursor.fetchall()
            
        return jsonify({
            'reflexoes': [dict(r) for r in reflexoes],
            'total_reflexoes': len(reflexoes)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug-diagnosticos')
def debug_diagnosticos():
    """Debug dos diagnósticos no banco"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT d.*, u.nome as usuario_nome 
                FROM diagnosticos d
                JOIN usuarios u ON d.usuario_id = u.id
                ORDER BY d.data_diagnostico DESC
            ''')
            diagnosticos = cursor.fetchall()
            
        return jsonify({
            'diagnosticos': [dict(d) for d in diagnosticos],
            'total_diagnosticos': len(diagnosticos)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug-dica')
def debug_dica():
    """Debug da dica do dia"""
    try:
        usuario_id = session.get('usuario_id', 1)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar último diagnóstico
            cursor.execute('''
                SELECT nivel FROM diagnosticos 
                WHERE usuario_id = %s 
                ORDER BY data_diagnostico DESC 
                LIMIT 1
            ''', (usuario_id,))
            diagnostico = cursor.fetchone()
            
            dica = obter_dica_do_dia(cursor, usuario_id)
            
            return jsonify({
                'usuario_id': usuario_id,
                'ultimo_diagnostico': diagnostico,
                'dica_do_dia': dica,
                'dia_do_ano': datetime.now().timetuple().tm_yday
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug-profissionais')
def debug_profissionais():
    """Debug dos profissionais no banco"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM profissionais 
                ORDER BY id DESC
            ''')
            profissionais = cursor.fetchall()
            
        return jsonify({
            'profissionais': [dict(prof) for prof in profissionais],
            'total_profissionais': len(profissionais)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug-instituicoes')
def debug_instituicoes():
    """Debug das instituições no banco"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM instituicoes 
                ORDER BY id DESC
            ''')
            instituicoes = cursor.fetchall()
            
        return jsonify({
            'instituicoes': [dict(inst) for inst in instituicoes],
            'total_instituicoes': len(instituicoes)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== INICIALIZAÇÃO ==========

if __name__ == '__main__':
    print("🚀 Inicializando NETENDENCIA com PostgreSQL AWS...")
    
    if not os.path.exists('templates'):
        os.makedirs('templates')
        print("📁 Pasta templates criada")
    
    init_database()
    
    print("✅ Sistema PostgreSQL inicializado com sucesso!")
    print("🌐 Acesse: http://localhost:5000/landing")
    print("📊 Avaliação Geral: http://localhost:5000/avaliacao-geral")
    print("🧪 Debug reflexões: http://localhost:5000/debug-reflexoes")
    print("🧪 Debug diagnósticos: http://localhost:5000/debug-diagnosticos")
    print("🧪 Debug dica: http://localhost:5000/debug-dica")
    print("🧪 Debug profissionais: http://localhost:5000/debug-profissionais")
    print("🧪 Debug instituições: http://localhost:5000/debug-instituicoes")
    print("📊 Dashboard: http://localhost:5000/ (após login)")
    
    app.run(debug=True, host='0.0.0.0', port=5000)