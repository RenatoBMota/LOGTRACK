#!/usr/bin/env python3
"""
Monitor de Separação - Sistema Completo com Autenticação e Roles
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
from sqlalchemy import inspect
import os
import csv
from io import StringIO, BytesIO
import json
from collections import defaultdict
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

# ============= CONFIGURAÇÃO DE TIMEZONE =============
# Fuso horário de Brasília (BRT/BRST) - UTC-3
BRT = timezone(timedelta(hours=-3))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sua-chave-secreta-aqui')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///monitor_separacao.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')

# ✅ Evita "database is locked" sob concorrência (várias abas/PWA/dashboard auto-refresh)
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'timeout': 30},   # espera até 30s por um lock liberar, em vez de falhar na hora
}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('instance', exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ✅ Ativa WAL mode no SQLite: permite leituras simultâneas durante uma escrita,
# o que elimina a maior parte dos travamentos de "database is locked"
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()

# ============= MODELOS =============

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    full_name = db.Column(db.String(120))
    role = db.Column(db.String(50), default='executor')  # admin, supervisor, executor
    status = db.Column(db.String(50), default='pending')  # pending, approved, rejected
    first_login = db.Column(db.Boolean, default=True)
    active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

class RolePermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50))  # admin, supervisor, executor
    permission = db.Column(db.String(100))  # dashboard, operation, cadastros, etc

class AppConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_name = db.Column(db.String(120), default='Monitor de Separação')
    app_description = db.Column(db.String(500))
    logo_filename = db.Column(db.String(255))
    primary_color = db.Column(db.String(7), default='#0066CC')
    secondary_color = db.Column(db.String(7), default='#1aa84a')

class Separator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    separator_id = db.Column(db.String(50))
    active = db.Column(db.Boolean, default=True)

class OperationUnit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(50))
    active = db.Column(db.Boolean, default=True)

class OperationLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    unit_id = db.Column(db.Integer)
    unit_name = db.Column(db.String(120))
    active = db.Column(db.Boolean, default=True)

class OccurrenceType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)

class LoadOperation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_type = db.Column(db.String(50))
    separator_1 = db.Column(db.Integer)
    separator_1_name = db.Column(db.String(120))
    separator_2 = db.Column(db.Integer)
    separator_2_name = db.Column(db.String(120))
    operation_type = db.Column(db.String(50))
    unit_id = db.Column(db.Integer)
    unit_name = db.Column(db.String(120))
    location_id = db.Column(db.Integer)
    location_name = db.Column(db.String(120))
    destination = db.Column(db.String(200))
    load_number = db.Column(db.String(100))
    weight_kg = db.Column(db.Float, default=0)
    sku_count = db.Column(db.Integer, default=0)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='Não Iniciado')
    occurrence_count = db.Column(db.Integer, default=0)
    created_by = db.Column(db.String(120))
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    # Agendamento
    scheduled_date = db.Column(db.DateTime, nullable=True)
    is_scheduled   = db.Column(db.Boolean, default=False)
    released_by    = db.Column(db.String(120), nullable=True)
    released_at    = db.Column(db.DateTime, nullable=True)
    # Pausa
    paused_at           = db.Column(db.DateTime, nullable=True)
    pause_reason        = db.Column(db.String(200), nullable=True)
    paused_by           = db.Column(db.String(120), nullable=True)
    total_pause_minutes = db.Column(db.Integer, default=0)

class Occurrence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    load_operation_id = db.Column(db.Integer)
    item_code = db.Column(db.String(100))
    description = db.Column(db.String(255))
    quantity = db.Column(db.Integer)
    occurrence_type = db.Column(db.String(120))

class SLAGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    metric = db.Column(db.String(120))
    target_value = db.Column(db.Float)
    unit = db.Column(db.String(50))
    active = db.Column(db.Boolean, default=True)

# ============= HELPER =============

def get_now_br():
    """Retorna a data/hora atual em horário de Brasília (BRT) - UTC-3"""
    return datetime.now(BRT)

def has_permission(page):
    """Verifica se usuário tem permissão para a página"""
    if not current_user.is_authenticated:
        return False
    perms = RolePermission.query.filter_by(role=current_user.role, permission=page).first()
    return perms is not None

@app.context_processor
def inject_config():
    config = AppConfig.query.first()
    if not config:
        config = AppConfig()
        db.session.add(config)
        db.session.commit()
    return dict(config=config, has_permission=has_permission)

# ============= LOGIN =============

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.status == 'approved' and user.check_password(password):
            login_user(user)
            if user.first_login:
                return redirect(url_for('change_password'))
            return redirect(url_for('dashboard'))
        else:
            error = 'Email ou senha incorretos, ou cadastro ainda não foi aprovado'
            return render_template('login.html', error=error)
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            full_name = request.form.get('full_name')
            
            if User.query.filter_by(email=email).first():
                return render_template('register.html', error='Email já registrado')
            
            user = User(email=email, full_name=full_name, status='pending', role='executor')
            db.session.add(user)
            db.session.commit()
            
            return render_template('register.html', success='Cadastro realizado! Aguarde aprovação.')
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro em register: {e}")
            return render_template('register.html', error='Erro ao cadastrar. Tente novamente.')
    
    return render_template('register.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        try:
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if new_password != confirm_password:
                return render_template('change_password.html', error='Senhas não conferem')
            
            current_user.set_password(new_password)
            current_user.first_login = False
            db.session.commit()
            
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro em change_password: {e}")
            return render_template('change_password.html', error='Erro ao alterar senha. Tente novamente.')
    
    return render_template('change_password.html')

# ============= ADMIN - APROVAÇÃO DE USUÁRIOS =============

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    pending = User.query.filter_by(status='pending').all()
    approved = User.query.filter_by(status='approved').all()
    
    return render_template('admin_users.html', pending=pending, approved=approved)

@app.route('/admin/approve/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    try:
        user = User.query.get(user_id)
        if user:
            user.status = 'approved'
            user.set_password('1234')  # Senha padrão
            user.first_login = True
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro em approve_user: {e}")
    return redirect(url_for('admin_users'))

@app.route('/admin/reject/<int:user_id>', methods=['POST'])
@login_required
def reject_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    try:
        user = User.query.get(user_id)
        if user:
            user.status = 'rejected'
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro em reject_user: {e}")
    return redirect(url_for('admin_users'))

@app.route('/admin/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user_admin(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    try:
        user = User.query.get(user_id)
        if user and user.id != current_user.id:
            db.session.delete(user)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro em delete_user_admin: {e}")
    return redirect(url_for('admin_users'))

@app.route('/admin/reset-password/<int:user_id>', methods=['POST'])
@login_required
def reset_password_admin(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    try:
        user = User.query.get(user_id)
        if user:
            user.set_password('1234')
            user.first_login = True
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro em reset_password_admin: {e}")
    return redirect(url_for('admin_users'))

@app.route('/admin/change-role/<int:user_id>', methods=['POST'])
@login_required
def change_user_role(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    try:
        user = User.query.get(user_id)
        new_role = request.form.get('role')
        if user and new_role in ['admin', 'supervisor', 'executor']:
            user.role = new_role
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro em change_user_role: {e}")
    return redirect(url_for('admin_users'))

# ============= ADMIN - PERMISSÕES =============

@app.route('/admin/permissions')
@login_required
def admin_permissions():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    pages = ['dashboard', 'operation', 'cadastros', 'relatorios', 'ocorrencias', 'sla', 'metas_sla', 'usuarios']
    roles = ['admin', 'supervisor', 'executor']
    
    permissions = {}
    for role in roles:
        permissions[role] = {}
        for page in pages:
            perm = RolePermission.query.filter_by(role=role, permission=page).first()
            permissions[role][page] = perm is not None
    
    return render_template('admin_permissions.html', permissions=permissions, pages=pages, roles=roles)

@app.route('/admin/permissions/update', methods=['POST'])
@login_required
def update_permissions():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    try:
        # Deletar todas as permissões
        RolePermission.query.delete()
        
        # Adicionar novas
        data = request.form.to_dict()
        for key, value in data.items():
            if value == 'on':
                # Split apenas no primeiro underscore
                parts = key.split('_', 1)
                if len(parts) == 2:
                    role, page = parts
                    perm = RolePermission(role=role, permission=page)
                    db.session.add(perm)
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro em update_permissions: {e}")
    return redirect(url_for('admin_permissions'))

# ============= ROTA RAIZ =============

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# ============= UPLOADS =============

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

# ============= DASHBOARD =============

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if not has_permission('dashboard'):
        return redirect(url_for('index'))
    
    from datetime import datetime, date
    
    separators = Separator.query.filter_by(active=True).all()
    units = OperationUnit.query.filter_by(active=True).all()
    locations = OperationLocation.query.filter_by(active=True).all()
    all_operations = LoadOperation.query.order_by(LoadOperation.created_date.desc()).all()
    sla_goals = SLAGoal.query.filter_by(active=True).all()
    
    # ✅ NOVO: Passar data de hoje como padrão (apenas no GET inicial)
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    
    # ✅ FILTRO: Se é GET, usa hoje. Se é POST, usa o que o usuário digitou
    if request.method == 'POST':
        filter_date_from_str = request.form.get('dataFrom', '')
        filter_date_to_str = request.form.get('dataTo', '')
    else:
        # GET inicial - mostra data de hoje no template mas não filtra
        filter_date_from_str = today_str
        filter_date_to_str = today_str
    
    try:
        if filter_date_from_str and filter_date_to_str:
            filter_date_from = datetime.strptime(filter_date_from_str, '%Y-%m-%d').date()
            filter_date_to = datetime.strptime(filter_date_to_str, '%Y-%m-%d').date()
            all_operations = [op for op in all_operations 
                            if op.start_time and 
                            filter_date_from <= op.start_time.date() <= filter_date_to]
    except:
        pass
    
    # ✅ NOVO: Filtro de data no Dashboard (CORRIGIDO - usa start_time)
    if request.method == 'POST':
        filter_date_from_str = request.form.get('dataFrom', '')
        filter_date_to_str = request.form.get('dataTo', '')
        
        try:
            if filter_date_from_str and filter_date_to_str:
                filter_date_from = datetime.strptime(filter_date_from_str, '%Y-%m-%d').date()
                filter_date_to = datetime.strptime(filter_date_to_str, '%Y-%m-%d').date()
                all_operations = [op for op in all_operations 
                                if op.start_time and 
                                filter_date_from <= op.start_time.date() <= filter_date_to]
            else:
                if filter_date_from_str:
                    filter_date_from = datetime.strptime(filter_date_from_str, '%Y-%m-%d').date()
                    all_operations = [op for op in all_operations 
                                    if op.created_date and op.created_date.date() >= filter_date_from]
                if filter_date_to_str:
                    filter_date_to = datetime.strptime(filter_date_to_str, '%Y-%m-%d').date()
                    all_operations = [op for op in all_operations 
                                    if op.created_date and op.created_date.date() <= filter_date_to]
        except:
            pass
    
    # ✅ Calcular métricas para o template
    finished_operations = [op for op in all_operations if op.status == 'Finalizado']
    
    # Tempo médio por SKU
    total_skus = sum(op.sku_count or 0 for op in finished_operations)
    total_time_minutes = sum(op.duration_minutes or 0 for op in finished_operations)
    
    if total_skus > 0:
        avg_time_per_sku_minutes = total_time_minutes / total_skus
        avg_time_per_sku_seconds = int(avg_time_per_sku_minutes * 60)  # Converter minutos para segundos
        hours = avg_time_per_sku_seconds // 3600
        minutes = (avg_time_per_sku_seconds % 3600) // 60
        seconds = avg_time_per_sku_seconds % 60
        avg_time_per_sku = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
    else:
        avg_time_per_sku = '--:--:--'
    
    # Tempo médio por tonelada — considera SOMENTE operações com peso informado (weight_kg > 0)
    finished_com_peso = [op for op in finished_operations if (op.weight_kg or 0) > 0]
    total_weight_kg = sum(op.weight_kg or 0 for op in finished_com_peso)
    total_time_com_peso = sum(op.duration_minutes or 0 for op in finished_com_peso)
    if total_weight_kg > 0:
        avg_time_per_ton_minutes = total_time_com_peso / (total_weight_kg / 1000)
        avg_time_per_ton_seconds = int(avg_time_per_ton_minutes * 60)
        hours = avg_time_per_ton_seconds // 3600
        minutes = (avg_time_per_ton_seconds % 3600) // 60
        seconds = avg_time_per_ton_seconds % 60
        avg_time_per_ton = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
    else:
        avg_time_per_ton = '--:--:--'
    
    # Tempo médio por carga
    if len(finished_operations) > 0:
        avg_time_per_load_minutes = total_time_minutes / len(finished_operations)
        avg_time_per_load_seconds = int(avg_time_per_load_minutes * 60)
        hours = avg_time_per_load_seconds // 3600
        minutes = (avg_time_per_load_seconds % 3600) // 60
        seconds = avg_time_per_load_seconds % 60
        avg_time_per_load = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
    else:
        avg_time_per_load = '--:--:--'
    
    # SKU por hora
    total_hours = total_time_minutes / 60 if total_time_minutes > 0 else 0
    sku_per_hour = round(total_skus / total_hours, 2) if total_hours > 0 else 0
    
    # Peso total
    total_weight_kg = sum(op.weight_kg or 0 for op in finished_operations)
    total_weight_str = f'{total_weight_kg:.0f} kg'
    
    return render_template('dashboard.html', 
                         separators=separators,
                         units=units,
                         locations=locations,
                         operations=all_operations,
                         sla_goals=sla_goals,
                         today_date=today_str,
                         filter_date_from_display=filter_date_from_str,
                         filter_date_to_display=filter_date_to_str,
                         avg_time_per_sku=avg_time_per_sku,
                         avg_time_per_ton=avg_time_per_ton,
                         avg_time_per_load=avg_time_per_load,
                         total_skus=total_skus,
                         sku_per_hour=sku_per_hour,
                         total_weight=total_weight_str)

# ============= OPERAÇÃO =============

@app.route('/operation', methods=['GET', 'POST'])
@login_required
def operation():
    if not has_permission('operation'):
        return redirect(url_for('dashboard'))
    
    from datetime import datetime, date
    separators = Separator.query.filter_by(active=True).all()
    units = OperationUnit.query.filter_by(active=True).all()
    locations = OperationLocation.query.filter_by(active=True).all()
    occurrence_types = OccurrenceType.query.filter_by(active=True).all()

    today = date.today()
    today_str = today.strftime('%Y-%m-%d')

    # Defaults: show today only on GET
    filter_date_from_str = today_str
    filter_date_to_str = today_str
    filter_status = ''
    filter_type = ''

    if request.method == 'POST':
        filter_date_from_str = request.form.get('filter_date_from', today_str)
        filter_date_to_str = request.form.get('filter_date_to', today_str)
        filter_status = request.form.get('filter_status', '')
        filter_type = request.form.get('filter_type', '')

    # Build query with date filter pushed to DB (fast)
    try:
        date_from = datetime.strptime(filter_date_from_str, '%Y-%m-%d')
        date_to = datetime.strptime(filter_date_to_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        q = LoadOperation.query.filter(
            LoadOperation.created_date >= date_from,
            LoadOperation.created_date <= date_to
        )
    except Exception:
        q = LoadOperation.query

    if filter_status:
        q = q.filter(LoadOperation.status == filter_status)
    if filter_type:
        q = q.filter(LoadOperation.operation_type == filter_type)

    all_operations = q.order_by(LoadOperation.created_date.desc()).all()

    # Load only occurrences for the operations currently shown
    op_ids = [op.id for op in all_operations]
    all_occurrences = Occurrence.query.filter(Occurrence.load_operation_id.in_(op_ids)).all() if op_ids else []
    
    not_started = [op for op in all_operations if op.status == 'Não Iniciado']
    in_progress = [op for op in all_operations if op.status == 'Em Andamento']

    def _sort_key(op):
        dt = op.end_time or op.created_date
        if dt is None:
            return datetime.min.replace(tzinfo=BRT)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=BRT)
        return dt

    finished = sorted(
        [op for op in all_operations if op.status == 'Finalizado'],
        key=_sort_key,
        reverse=True
    )
    
    return render_template('operation.html',
                         separators=separators,
                         units=units,
                         locations=locations,
                         occurrence_types=occurrence_types,
                         operations=all_operations,
                         occurrences=all_occurrences,
                         not_started=not_started,
                         in_progress=in_progress,
                         finished=finished,
                         today_date=today_str,
                         filter_date_from_display=filter_date_from_str,
                         filter_date_to_display=filter_date_to_str)

@app.route('/operation/create', methods=['POST'])
@login_required
def create_operation():
    try:
        load_number = request.form.get('load_number')
        operation_type = request.form.get('operation_type')
        team_type = request.form.get('team_type', 'Individual')
        separator_1 = request.form.get('separator_1')
        separator_2 = request.form.get('separator_2')
        unit_id = request.form.get('unit_id')
        location_id = request.form.get('location_id')
        destination = request.form.get('destination', '')
        sku_count = request.form.get('sku_count', 0)
        weight_kg = request.form.get('weight_kg', 0)
        
        sep1_name = ''
        if separator_1:
            sep = Separator.query.get(separator_1)
            sep1_name = sep.full_name if sep else ''
        
        sep2_name = ''
        if separator_2:
            sep = Separator.query.get(separator_2)
            sep2_name = sep.full_name if sep else ''
        
        unit_name = ''
        if unit_id:
            unit = OperationUnit.query.get(unit_id)
            unit_name = unit.name if unit else ''
        
        location_name = ''
        if location_id:
            location = OperationLocation.query.get(location_id)
            location_name = location.name if location else ''
        
        operation = LoadOperation(
            load_number=load_number,
            operation_type=operation_type,
            team_type=team_type,
            separator_1=separator_1,
            separator_1_name=sep1_name,
            separator_2=separator_2,
            separator_2_name=sep2_name,
            unit_id=unit_id,
            unit_name=unit_name,
            location_id=location_id,
            location_name=location_name,
            destination=destination,
            sku_count=int(sku_count),
            weight_kg=float(weight_kg) if weight_kg else 0,
            status='Não Iniciado',
            created_by=current_user.email
        )
        
        # Agendamento
        scheduled_date_str = request.form.get('scheduled_date', '').strip()
        if scheduled_date_str:
            try:
                scheduled_dt = datetime.strptime(scheduled_date_str, '%Y-%m-%dT%H:%M')
                operation.scheduled_date = scheduled_dt
                operation.is_scheduled   = True
                operation.status         = 'Agendado'
            except:
                pass

        db.session.add(operation)
        db.session.commit()
    except:
        db.session.rollback()
    
    return redirect(url_for('operation'))

@app.route('/operation/<int:op_id>/start', methods=['POST'])
@login_required
def start_operation(op_id):
    try:
        operation = LoadOperation.query.get(op_id)
        if operation:
            operation.status = 'Em Andamento'
            operation.start_time = get_now_br()
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro em start_operation: {e}")
    return redirect(url_for('operation'))

@app.route('/operation/<int:op_id>/finish', methods=['POST'])
@login_required
def finish_operation(op_id):
    try:
        operation = LoadOperation.query.get(op_id)
        if operation:
            operation.status = 'Finalizado'
            operation.end_time = get_now_br()
            if operation.start_time:
                if operation.start_time.tzinfo is None:
                    start_time_aware = operation.start_time.replace(tzinfo=BRT)
                else:
                    start_time_aware = operation.start_time
                delta = operation.end_time - start_time_aware
                total_minutes = int(delta.total_seconds() / 60)
                # Descontar tempo de pausa acumulado
                pause_minutes = operation.total_pause_minutes or 0
                operation.duration_minutes = max(0, total_minutes - pause_minutes)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro em finish_operation: {e}")
    return redirect(url_for('operation'))

@app.route('/operation/<int:op_id>/delete', methods=['POST', 'GET'])
@login_required
def delete_operation(op_id):
    try:
        # ✅ BLOQUEIO: Operadores não podem deletar
        if current_user.role == 'executor':
            return redirect(url_for('operation'))
        
        operation = LoadOperation.query.get(op_id)
        if operation:
            Occurrence.query.filter_by(load_operation_id=op_id).delete()
            db.session.delete(operation)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro em delete_operation: {e}")
    return redirect(url_for('operation'))

@app.route('/operation/<int:op_id>/edit', methods=['POST'])
@login_required
def edit_operation(op_id):
    if current_user.role == 'executor':
        return redirect(url_for('operation'))
    try:
        operation = LoadOperation.query.get(op_id)
        if operation:
            # Dados básicos
            operation.load_number    = request.form.get('load_number',    operation.load_number)
            operation.operation_type = request.form.get('operation_type', operation.operation_type)
            operation.team_type      = request.form.get('team_type',      operation.team_type)
            operation.destination    = request.form.get('destination',    operation.destination)
            operation.sku_count      = int(request.form.get('sku_count')  or operation.sku_count or 0)
            operation.weight_kg      = float(request.form.get('weight_kg') or operation.weight_kg or 0)
            # Separadores
            sep1_id   = request.form.get('separator_1')
            sep1_name = request.form.get('separator_1_name', operation.separator_1_name)
            if sep1_id:
                operation.separator_1      = int(sep1_id)
                sep1_obj = Separator.query.get(int(sep1_id))
                operation.separator_1_name = sep1_obj.full_name if sep1_obj else sep1_name
            sep2_id   = request.form.get('separator_2')
            sep2_name = request.form.get('separator_2_name', operation.separator_2_name)
            if sep2_id:
                operation.separator_2      = int(sep2_id)
                sep2_obj = Separator.query.get(int(sep2_id))
                operation.separator_2_name = sep2_obj.full_name if sep2_obj else sep2_name
            # Unidade e Local
            unit_id = request.form.get('unit_id')
            if unit_id:
                operation.unit_id = int(unit_id)
                unit = OperationUnit.query.get(int(unit_id))
                operation.unit_name = unit.name if unit else operation.unit_name
            location_id = request.form.get('location_id')
            if location_id:
                operation.location_id = int(location_id)
                loc = OperationLocation.query.get(int(location_id))
                operation.location_name = loc.name if loc else operation.location_name
            # Agendamento (só ADM pode alterar)
            if current_user.role == 'admin':
                sched_str = request.form.get('scheduled_date', '').strip()
                if sched_str:
                    try:
                        operation.scheduled_date = datetime.strptime(sched_str, '%Y-%m-%dT%H:%M')
                        operation.is_scheduled   = True
                        if operation.status not in ('Em Andamento', 'Finalizado'):
                            operation.status = 'Agendado'
                    except:
                        pass
                elif request.form.get('clear_schedule') == '1':
                    operation.scheduled_date = None
                    operation.is_scheduled   = False
                    if operation.status == 'Agendado':
                        operation.status = 'Não Iniciado'
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro em edit_operation: {e}")
        import traceback; traceback.print_exc()
    return redirect(url_for('operation'))

# ── Liberação de operação agendada (apenas ADM) ──
@app.route('/operation/<int:op_id>/release', methods=['POST'])
@login_required
def release_operation(op_id):
    if current_user.role != 'admin':
        return redirect(url_for('operation'))
    try:
        operation = LoadOperation.query.get(op_id)
        if operation and operation.status == 'Agendado':
            operation.status      = 'Não Iniciado'
            operation.released_by = current_user.email
            operation.released_at = get_now_br()
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro em release_operation: {e}")
    return redirect(url_for('operation'))

# ── Pausar operação ──
@app.route('/operation/<int:op_id>/pause', methods=['POST'])
@login_required
def pause_operation(op_id):
    try:
        operation = LoadOperation.query.get(op_id)
        if not operation or operation.status != 'Em Andamento':
            return redirect(url_for('operation'))
        # Só quem iniciou pode pausar (ou admin)
        if current_user.role != 'admin' and operation.separator_1_name != current_user.full_name and operation.separator_2_name != current_user.full_name:
            return redirect(url_for('operation'))
        pause_reason = request.form.get('pause_reason', 'Intervalo')
        operation.status      = 'Pausado'
        operation.paused_at   = get_now_br()
        operation.pause_reason = pause_reason
        operation.paused_by   = current_user.email
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro em pause_operation: {e}")
    return redirect(url_for('operation'))

# ── Retomar operação pausada ──
@app.route('/operation/<int:op_id>/resume', methods=['POST'])
@login_required
def resume_operation(op_id):
    try:
        operation = LoadOperation.query.get(op_id)
        if not operation or operation.status != 'Pausado':
            return redirect(url_for('operation'))
        if current_user.role != 'admin' and operation.separator_1_name != current_user.full_name and operation.separator_2_name != current_user.full_name:
            return redirect(url_for('operation'))
        # Acumula tempo de pausa
        if operation.paused_at:
            now = get_now_br()
            paused_at = operation.paused_at
            if paused_at.tzinfo is None:
                paused_at = paused_at.replace(tzinfo=BRT)
            pause_duration = int((now - paused_at).total_seconds() / 60)
            operation.total_pause_minutes = (operation.total_pause_minutes or 0) + pause_duration
        operation.status     = 'Em Andamento'
        operation.paused_at  = None
        operation.pause_reason = None
        operation.paused_by  = None
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro em resume_operation: {e}")
    return redirect(url_for('operation'))

@app.route('/operation/<int:op_id>/occurrence/add', methods=['POST'])
@login_required
def add_occurrence(op_id):
    try:
        print(f"\n{'='*60}")
        print(f"ADICIONANDO OCORRÊNCIA - Operation ID: {op_id}")
        print(f"Form data: {dict(request.form)}")
        
        ocurrences_added = 0
        
        # Procurar por todos os campos de ocorrência
        for key in request.form:
            if key.startswith('item_code_'):
                idx = key.split('_')[-1]
                item_code = request.form.get(f'item_code_{idx}', '').strip()
                description = request.form.get(f'description_{idx}', '').strip()
                quantity_str = request.form.get(f'quantity_{idx}', '0').strip()
                occ_type = request.form.get(f'occurrence_type_{idx}', '').strip()
                
                print(f"\nCampo {idx}:")
                print(f"  item_code: {item_code}")
                print(f"  description: {description}")
                print(f"  quantity: {quantity_str}")
                print(f"  type: {occ_type}")
                
                # Apenas salvar se tem código do item (campo obrigatório)
                if item_code:
                    try:
                        quantity = int(quantity_str) if quantity_str else 0
                    except ValueError:
                        quantity = 0
                    
                    occurrence = Occurrence(
                        load_operation_id=op_id,
                        item_code=item_code,
                        description=description,
                        quantity=quantity,
                        occurrence_type=occ_type
                    )
                    db.session.add(occurrence)
                    ocurrences_added += 1
                    print(f"  ✅ Ocorrência adicionada à sessão")
        
        print(f"\nTotal de ocorrências a adicionar: {ocurrences_added}")
        
        if ocurrences_added > 0:
            # Atualizar contador de ocorrências na operação
            operation = LoadOperation.query.get(op_id)
            if operation:
                # Contar total de ocorrências para esta operação
                total_occurrences = Occurrence.query.filter_by(load_operation_id=op_id).count()
                operation.occurrence_count = total_occurrences
                print(f"Atualizando contador: {total_occurrences} ocorrências no total")
            
            db.session.commit()
            print(f"✅ {ocurrences_added} ocorrência(s) salva(s) com sucesso!")
        else:
            print("⚠️ Nenhuma ocorrência foi adicionada (sem item_code)")
            
        print(f"{'='*60}\n")
        
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ ERRO ao adicionar ocorrência:")
        print(f"   {type(e).__name__}: {str(e)}")
        print(f"{'='*60}\n")
    
    return redirect(url_for('operation'))

# ✅ MELHORIA #3: Rota para deletar ocorrência
@app.route('/operation/<int:op_id>/occurrence/<int:occ_id>/delete', methods=['POST'])
@login_required
def delete_occurrence(op_id, occ_id):
    try:
        occurrence = Occurrence.query.get(occ_id)
        if occurrence and occurrence.load_operation_id == op_id:
            db.session.delete(occurrence)
            
            # Atualizar contador
            operation = LoadOperation.query.get(op_id)
            if operation:
                operation.occurrence_count = Occurrence.query.filter_by(load_operation_id=op_id).count()
            
            db.session.commit()
    except:
        db.session.rollback()
    
    return redirect(url_for('operation'))

# ✅ MELHORIA #3: Rota para editar ocorrência
@app.route('/operation/<int:op_id>/occurrence/<int:occ_id>/edit', methods=['POST'])
@login_required
def edit_occurrence(op_id, occ_id):
    try:
        occurrence = Occurrence.query.get(occ_id)
        if occurrence and occurrence.load_operation_id == op_id:
            occurrence.item_code = request.form.get('item_code', occurrence.item_code)
            occurrence.description = request.form.get('description', occurrence.description)
            occurrence.quantity = int(request.form.get('quantity', occurrence.quantity))
            occurrence.occurrence_type = request.form.get('occurrence_type', occurrence.occurrence_type)
            db.session.commit()
    except:
        db.session.rollback()
    
    return redirect(url_for('operation'))

# ============= CADASTROS =============

@app.route('/registrations')
@login_required
def registrations():
    if not has_permission('cadastros'):
        return redirect(url_for('dashboard'))
    
    separators = Separator.query.all()
    units = OperationUnit.query.all()
    locations = OperationLocation.query.all()
    occurrence_types = OccurrenceType.query.all()
    
    return render_template('cadastros.html',
                         separators=separators,
                         units=units,
                         locations=locations,
                         occurrence_types=occurrence_types)

@app.route('/registrations/separator/add', methods=['POST'])
@login_required
def add_separator():
    try:
        name = request.form.get('name')
        sep_id = request.form.get('sep_id')
        sep = Separator(full_name=name, separator_id=sep_id)
        db.session.add(sep)
        db.session.commit()
    except:
        db.session.rollback()
    return redirect(url_for('registrations'))

@app.route('/registrations/unit/add', methods=['POST'])
@login_required
def add_unit():
    try:
        name = request.form.get('name')
        code = request.form.get('code')
        unit = OperationUnit(name=name, code=code)
        db.session.add(unit)
        db.session.commit()
    except:
        db.session.rollback()
    return redirect(url_for('registrations'))

@app.route('/registrations/location/add', methods=['POST'])
@login_required
def add_location():
    try:
        name = request.form.get('name')
        unit_id = request.form.get('unit_id')
        
        # Obter nome da unidade
        unit_name = ''
        if unit_id:
            unit = OperationUnit.query.get(unit_id)
            unit_name = unit.name if unit else ''
        
        location = OperationLocation(name=name, unit_id=unit_id, unit_name=unit_name)
        db.session.add(location)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
    return redirect(url_for('registrations'))

@app.route('/registrations/occ-type/add', methods=['POST'])
@login_required
def add_occurrence_type():
    try:
        name = request.form.get('name')
        desc = request.form.get('description')
        oc = OccurrenceType(name=name, description=desc)
        db.session.add(oc)
        db.session.commit()
    except:
        db.session.rollback()
    return redirect(url_for('registrations'))

@app.route('/registrations/separator/<int:id>/delete', methods=['POST'])
@login_required
def delete_separator(id):
    try:
        item = Separator.query.get(id)
        if item:
            db.session.delete(item)
            db.session.commit()
    except:
        db.session.rollback()
    return redirect(url_for('registrations'))

@app.route('/registrations/unit/<int:id>/delete', methods=['POST'])
@login_required
def delete_unit(id):
    try:
        item = OperationUnit.query.get(id)
        if item:
            db.session.delete(item)
            db.session.commit()
    except:
        db.session.rollback()
    return redirect(url_for('registrations'))

@app.route('/registrations/location/<int:id>/delete', methods=['POST'])
@login_required
def delete_location(id):
    try:
        item = OperationLocation.query.get(id)
        if item:
            db.session.delete(item)
            db.session.commit()
    except:
        db.session.rollback()
    return redirect(url_for('registrations'))

@app.route('/registrations/occ-type/<int:id>/delete', methods=['POST'])
@login_required
def delete_occ_type(id):
    try:
        item = OccurrenceType.query.get(id)
        if item:
            db.session.delete(item)
            db.session.commit()
    except:
        db.session.rollback()
    return redirect(url_for('registrations'))

# ============= RELATÓRIOS =============

@app.route('/reports')
@login_required
def reports():
    if not has_permission('relatorios'):
        return redirect(url_for('dashboard'))
    
    operations = LoadOperation.query.all()
    return render_template('relatorios.html', operations=operations)

@app.route('/reports/export')
@login_required
def export_reports():
    operations = LoadOperation.query.all()
    output = StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Carga', 'Tipo', 'Equipe', 'Separador', 'Unidade', 'Local', 'Peso', 'SKUs', 'Início', 'Fim', 'Duração', 'Status'])
    
    for op in operations:
        writer.writerow([
            op.load_number or '',
            op.operation_type or '',
            op.team_type or '',
            op.separator_1_name or '',
            op.unit_name or '',
            op.location_name or '',
            op.weight_kg or '',
            op.sku_count or '',
            op.start_time.strftime('%d/%m/%Y %H:%M:%S') if op.start_time else '',
            op.end_time.strftime('%d/%m/%Y %H:%M:%S') if op.end_time else '',
            op.duration_minutes or '',
            op.status or ''
        ])
    
    output.seek(0)
    response = app.response_class(response=output.getvalue(), status=200, mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=relatorio_operacoes.csv"
    return response

@app.route('/occurrence-report')
@login_required
def occurrence_report():
    if not has_permission('ocorrencias'):
        return redirect(url_for('dashboard'))

    occurrences = Occurrence.query.all()
    separators = Separator.query.filter_by(active=True).all()
    units = OperationUnit.query.filter_by(active=True).all()
    occurrence_types = OccurrenceType.query.filter_by(active=True).all()

    # Contagem por tipo para o gráfico
    tipo_counts = defaultdict(int)
    for occ in occurrences:
        tipo_counts[occ.occurrence_type or 'Sem tipo'] += 1
    tipo_labels = list(tipo_counts.keys())
    tipo_data   = list(tipo_counts.values())

    return render_template('ocorrencias.html',
                         occurrences=occurrences,
                         separators=separators,
                         units=units,
                         occurrence_types=occurrence_types,
                         tipo_labels=tipo_labels,
                         tipo_data=tipo_data)

@app.route('/relatorios')
@login_required
def relatorios():
    if not has_permission('relatorios'):
        return redirect(url_for('dashboard'))

    query = LoadOperation.query

    # Filtros GET
    date_from      = request.args.get('date_from', '')
    date_to        = request.args.get('date_to', '')
    location_id    = request.args.get('location_id', '')
    filter_status  = request.args.get('status', '')
    filter_type    = request.args.get('operation_type', '')

    if date_from:
        try:
            dt_from = datetime.strptime(date_from, '%Y-%m-%d')
            # start_time para iniciadas/finalizadas, created_date para não iniciadas/agendadas
            query = query.filter(
                db.or_(
                    LoadOperation.start_time >= dt_from,
                    db.and_(LoadOperation.start_time == None, LoadOperation.created_date >= dt_from)
                )
            )
        except: pass
    if date_to:
        try:
            dt_to = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(
                db.or_(
                    LoadOperation.start_time <= dt_to,
                    db.and_(LoadOperation.start_time == None, LoadOperation.created_date <= dt_to)
                )
            )
        except: pass
    if location_id:
        try:
            query = query.filter(LoadOperation.location_id == int(location_id))
        except: pass
    if filter_status:
        query = query.filter(LoadOperation.status == filter_status)
    if filter_type:
        query = query.filter(LoadOperation.operation_type == filter_type)

    operations        = query.order_by(LoadOperation.created_date.desc()).all()
    occurrences       = Occurrence.query.all()
    separators        = Separator.query.filter_by(active=True).all()
    occurrence_types  = OccurrenceType.query.filter_by(active=True).all()
    units             = OperationUnit.query.filter_by(active=True).all()
    locations         = OperationLocation.query.filter_by(active=True).all()

    return render_template('relatorios.html',
                           operations=operations,
                           occurrences=occurrences,
                           separators=separators,
                           occurrence_types=occurrence_types,
                           units=units,
                           locations=locations,
                           filter_date_from=date_from,
                           filter_date_to=date_to,
                           filter_location_id=location_id,
                           filter_status=filter_status,
                           filter_type=filter_type)

@app.route('/relatorios/export')
@login_required
def export_relatorios():
    operations = LoadOperation.query.all()
    output = StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['ID', 'Separador 1', 'Separador 2', 'SKUs', 'Peso (kg)', 'Duração', 'Status', 'Data'])
    
    for op in operations:
        writer.writerow([
            op.id or '',
            op.separator_1_name or '',
            op.separator_2_name or '',
            op.sku_count or '',
            op.weight_kg or '',
            op.duration_minutes or '',
            op.status or '',
            op.created_date.strftime('%d/%m/%Y %H:%M') if op.created_date else ''
        ])
    
    output.seek(0)
    response = app.response_class(response=output.getvalue(), status=200, mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=relatorio_operacoes.csv"
    return response

@app.route('/occurrence-report/export')
@login_required
def export_occurrences():
    occurrences = Occurrence.query.all()
    output = StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Carga', 'Código Item', 'Descrição', 'Quantidade', 'Tipo Ocorrência'])
    
    for oc in occurrences:
        writer.writerow([oc.load_operation_id or '', oc.item_code or '', oc.description or '', oc.quantity or '', oc.occurrence_type or ''])
    
    output.seek(0)
    response = app.response_class(response=output.getvalue(), status=200, mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=relatorio_ocorrencias.csv"
    return response

# ============= SLA =============

@app.route('/sla', methods=['GET', 'POST'])
@login_required
def sla():
    if not has_permission('sla'):
        return redirect(url_for('dashboard'))
    
    from datetime import datetime, date
    
    operations = LoadOperation.query.all()
    sla_goals = SLAGoal.query.filter_by(active=True).all()
    units = OperationUnit.query.filter_by(active=True).all()
    locations = OperationLocation.query.filter_by(active=True).all()
    
    # ✅ MESMO PENSAMENTO DO DASHBOARD: Inicializar datas
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    
    # ✅ FILTRO SIMPLES: Pega datas do formulário
    filter_date_from_str = request.form.get('filter_date_from', today_str) if request.method == 'POST' else today_str
    filter_date_to_str = request.form.get('filter_date_to', today_str) if request.method == 'POST' else today_str
    
    # ✅ Aplica filtro simples
    try:
        if filter_date_from_str:
            date_from = datetime.strptime(filter_date_from_str, '%Y-%m-%d').date()
            operations = [op for op in operations if op.created_date and op.created_date.date() >= date_from]
        if filter_date_to_str:
            date_to = datetime.strptime(filter_date_to_str, '%Y-%m-%d').date()
            operations = [op for op in operations if op.created_date and op.created_date.date() <= date_to]
    except:
        pass
    
    # ✅ MELHORIA #6: Calcular ranking de violações por colaborador
    violations_by_separator = {}
    finalizados_hoje = 0  # Contar operações finalizadas
    
    for op in operations:
        # Contar finalizados
        if op.status == 'Finalizado':
            finalizados_hoje += 1
        
        if op.status == 'Finalizado':
            # Verificar se violou alguma meta
            violated = False
            
            for goal in sla_goals:
                if goal.metric == 'tempo_medio_sku' and op.sku_count > 0:
                    time_per_sku = op.duration_minutes / op.sku_count
                    if time_per_sku > goal.target_value:
                        violated = True
                elif goal.metric == 'tempo_medio_tonelada' and op.weight_kg > 0:
                    time_per_ton = op.duration_minutes / (op.weight_kg / 1000)
                    if time_per_ton > goal.target_value:
                        violated = True
                elif goal.metric == 'tempo_medio_carregamento':
                    if op.duration_minutes > goal.target_value:
                        violated = True
            
            # Registrar violação para cada separador
            if violated:
                sep_name = op.separator_1_name or 'Desconhecido'
                if sep_name not in violations_by_separator:
                    violations_by_separator[sep_name] = {'violations': 0, 'total_ops': 0}
                violations_by_separator[sep_name]['violations'] += 1
                
                if op.separator_2_name:
                    sep_name_2 = op.separator_2_name
                    if sep_name_2 not in violations_by_separator:
                        violations_by_separator[sep_name_2] = {'violations': 0, 'total_ops': 0}
                    violations_by_separator[sep_name_2]['violations'] += 1
    
    # Contar total de operações por separador
    for op in operations:
        if op.separator_1_name:
            sep_name = op.separator_1_name
            if sep_name not in violations_by_separator:
                violations_by_separator[sep_name] = {'violations': 0, 'total_ops': 0}
            violations_by_separator[sep_name]['total_ops'] += 1
        
        if op.separator_2_name:
            sep_name_2 = op.separator_2_name
            if sep_name_2 not in violations_by_separator:
                violations_by_separator[sep_name_2] = {'violations': 0, 'total_ops': 0}
            violations_by_separator[sep_name_2]['total_ops'] += 1
    
    # Calcular percentual e ordenar
    violations_ranking = []
    for sep_name, data in violations_by_separator.items():
        percentage = (data['violations'] / data['total_ops'] * 100) if data['total_ops'] > 0 else 0
        violations_ranking.append({
            'separator': sep_name,
            'violations': data['violations'],
            'total_operations': data['total_ops'],
            'percentage': round(percentage, 2)
        })
    
    # Ordenar por número de violações (decrescente)
    violations_ranking.sort(key=lambda x: x['violations'], reverse=True)
    
    # ✅ CORRIGIDO: Adicionar locations para o dropdown
    locations = OperationLocation.query.filter_by(active=True).all()
    
    return render_template('sla.html', 
                         operations=operations, 
                         sla_goals=sla_goals, 
                         units=units,
                         locations=locations,
                         violations_ranking=violations_ranking,
                         finalizados_hoje=finalizados_hoje,
                         filter_date_from_display=filter_date_from_str,
                         filter_date_to_display=filter_date_to_str,
                         today_date=today_str)

@app.route('/cadastros')
@login_required
def cadastros():
    if not has_permission('cadastros'):
        return redirect(url_for('dashboard'))
    
    separators = Separator.query.all()
    units = OperationUnit.query.all()
    locations = OperationLocation.query.all()
    occurrence_types = OccurrenceType.query.all()
    
    return render_template('cadastros.html', 
                         separators=separators, 
                         units=units, 
                         locations=locations,
                         occurrence_types=occurrence_types)

@app.route('/sla-goals')
@login_required
def sla_goals():
    if not has_permission('metas_sla'):
        return redirect(url_for('dashboard'))
    
    # Garantir que as 5 metas padrão existem
    try:
        if SLAGoal.query.count() == 0:
            sla_metas = [
                SLAGoal(name='Tempo Médio por SKU', metric='tempo_medio_sku', target_value=2.0, unit='min', active=True),
                SLAGoal(name='Tempo Médio por Tonelada', metric='tempo_medio_tonelada', target_value=5.0, unit='min', active=True),
                SLAGoal(name='Tempo Médio por Carregamento', metric='tempo_medio_carregamento', target_value=40.0, unit='min', active=True),
                SLAGoal(name='Máx. Ocorrências por Dia', metric='max_ocorrencias_dia', target_value=5.0, unit='qtd', active=True),
                SLAGoal(name='SKU por Hora', metric='sku_por_hora', target_value=60.0, unit='SKU/h', active=True),
            ]
            for meta in sla_metas:
                db.session.add(meta)
            db.session.commit()
    except:
        pass
    
    goals = SLAGoal.query.all()
    return render_template('metas_sla.html', goals=goals)

@app.route('/sla-goals/add', methods=['POST'])
@login_required
def add_sla_goal():
    # DESABILITADO: Sistema funciona apenas com 5 metas padrão
    # Não é possível adicionar metas customizadas
    return redirect(url_for('sla_goals'))

@app.route('/sla-goals/<int:id>/edit', methods=['POST'])
@login_required
def edit_sla_goal(id):
    try:
        goal = SLAGoal.query.get(id)
        if goal:
            value_str = request.form.get('value', str(goal.target_value))
            
            # Converter HH:MM:SS para minutos se necessário
            if ':' in value_str:
                parts = value_str.split(':')
                if len(parts) == 3:
                    hours = int(parts[0]) or 0
                    minutes = int(parts[1]) or 0
                    seconds = int(parts[2]) or 0
                    goal.target_value = hours * 60 + minutes + (seconds / 60)
                else:
                    goal.target_value = float(value_str)
            else:
                goal.target_value = float(value_str)
            
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao editar meta SLA: {e}")
    return redirect(url_for('sla_goals'))

# ============= USUÁRIOS =============

@app.route('/users')
@login_required
def users():
    if not has_permission('usuarios'):
        return redirect(url_for('dashboard'))
    
    users_list = User.query.all()
    return render_template('usuarios.html', users=users_list)

# ============= CONFIGURAÇÕES =============

@app.route('/settings')
@login_required
def settings():
    try:
        config = AppConfig.query.first()
        if not config:
            config = AppConfig()
            db.session.add(config)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro em settings: {e}")
        config = AppConfig.query.first()
    
    return render_template('settings.html', config=config)

@app.route('/settings/save', methods=['POST'])
@login_required
def save_settings():
    try:
        config = AppConfig.query.first()
        if not config:
            config = AppConfig()
            db.session.add(config)
        
        config.app_name = request.form.get('app_name', config.app_name)
        config.app_description = request.form.get('app_description', config.app_description)
        config.primary_color = request.form.get('primary_color', config.primary_color)
        config.secondary_color = request.form.get('secondary_color', config.secondary_color)
        
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                config.logo_filename = filename
        
        db.session.commit()
        return redirect(url_for('settings'))
    except:
        db.session.rollback()
        return redirect(url_for('settings'))

# ============= RANKING DE SEPARADORES =============

@app.route('/ranking')
@login_required
def ranking():
    if not has_permission('relatorios'):
        return redirect(url_for('dashboard'))

    today_str     = datetime.utcnow().strftime('%Y-%m-%d')
    date_from_str = request.args.get('date_from', today_str)
    date_to_str   = request.args.get('date_to', today_str)
    f_unit        = request.args.get('unit_id', '')
    f_location    = request.args.get('location_id', '')
    f_type        = request.args.get('operation_type', '')
    f_separator   = request.args.get('separator', '')

    query = LoadOperation.query.filter(LoadOperation.status == 'Finalizado')
    try:
        query = query.filter(LoadOperation.end_time >= datetime.strptime(date_from_str, '%Y-%m-%d'))
    except ValueError:
        pass
    try:
        dt_to = datetime.strptime(date_to_str, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(LoadOperation.end_time < dt_to)
    except ValueError:
        pass
    if f_unit:
        query = query.filter(LoadOperation.unit_id == int(f_unit))
    if f_location:
        query = query.filter(LoadOperation.location_id == int(f_location))
    if f_type:
        query = query.filter(LoadOperation.operation_type == f_type)

    operations = query.all()
    if f_separator:
        operations = [op for op in operations if f_separator.lower() in (op.separator_1_name or '').lower()
                      or f_separator.lower() in (op.separator_2_name or '').lower()]

    occurrences = Occurrence.query.all()
    occ_by_op = defaultdict(list)
    for occ in occurrences:
        occ_by_op[occ.load_operation_id].append(occ)

    sep_stats = {}
    for op in operations:
        names = []
        if op.separator_1_name:
            names.append(op.separator_1_name)
        if op.separator_2_name:
            names.append(op.separator_2_name)
        for name in names:
            if name not in sep_stats:
                sep_stats[name] = {'ops': 0, 'ocorrencias': 0, 'total_min': 0}
            sep_stats[name]['ops'] += 1
            sep_stats[name]['ocorrencias'] += len(occ_by_op[op.id])
            sep_stats[name]['total_min'] += op.duration_minutes or 0

    ranking_list = []
    for name, s in sep_stats.items():
        ranking_list.append({
            'nome': name,
            'ops': s['ops'],
            'ocorrencias': s['ocorrencias'],
            'tempo_medio': round(s['total_min'] / s['ops']) if s['ops'] else 0,
        })
    ranking_list.sort(key=lambda x: x['ops'], reverse=True)

    units     = OperationUnit.query.filter_by(active=True).all()
    locations = OperationLocation.query.filter_by(active=True).all()

    return render_template('ranking.html',
                           ranking=ranking_list,
                           date_from=date_from_str,
                           date_to=date_to_str,
                           units=units,
                           locations=locations,
                           f_unit=f_unit,
                           f_location=f_location,
                           f_type=f_type,
                           f_separator=f_separator)


# ============= RELATÓRIO SLA =============

@app.route('/sla-relatorio')
@login_required
def sla_relatorio():
    if not has_permission('relatorios'):
        return redirect(url_for('dashboard'))

    today_str     = datetime.utcnow().strftime('%Y-%m-%d')
    date_from_str = request.args.get('date_from', today_str)
    date_to_str   = request.args.get('date_to', today_str)
    f_unit        = request.args.get('unit_id', '')
    f_location    = request.args.get('location_id', '')
    f_type        = request.args.get('operation_type', '')

    query = LoadOperation.query.filter(LoadOperation.status == 'Finalizado')
    try:
        query = query.filter(LoadOperation.end_time >= datetime.strptime(date_from_str, '%Y-%m-%d'))
    except ValueError:
        pass
    try:
        dt_to = datetime.strptime(date_to_str, '%Y-%m-%d') + timedelta(days=1)
        query = query.filter(LoadOperation.end_time < dt_to)
    except ValueError:
        pass
    if f_unit:
        query = query.filter(LoadOperation.unit_id == int(f_unit))
    if f_location:
        query = query.filter(LoadOperation.location_id == int(f_location))
    if f_type:
        query = query.filter(LoadOperation.operation_type == f_type)

    operations = query.all()
    sla_goals = SLAGoal.query.filter_by(active=True).all()
    units     = OperationUnit.query.filter_by(active=True).all()
    locations = OperationLocation.query.filter_by(active=True).all()

    def avalia_op(op, goals):
        resultados = []
        for goal in goals:
            try:
                if goal.metric == 'tempo_medio_sku' and op.sku_count:
                    valor = op.duration_minutes / op.sku_count
                    dentro = valor <= goal.target_value
                elif goal.metric == 'tempo_medio_tonelada' and op.weight_kg:
                    valor = op.duration_minutes / (op.weight_kg / 1000)
                    dentro = valor <= goal.target_value
                elif goal.metric == 'tempo_medio_carregamento':
                    valor = op.duration_minutes
                    dentro = valor <= goal.target_value
                elif goal.metric == 'sku_por_hora' and op.duration_minutes:
                    valor = (op.sku_count / op.duration_minutes) * 60
                    dentro = valor >= goal.target_value
                else:
                    continue
                resultados.append({'meta': goal.name, 'dentro': dentro, 'valor': round(valor, 2), 'alvo': goal.target_value, 'unit': goal.unit})
            except (ZeroDivisionError, TypeError):
                continue
        return resultados

    rows = []
    meta_stats = defaultdict(lambda: {'dentro': 0, 'fora': 0})
    for op in operations:
        res = avalia_op(op, sla_goals)
        dentro_geral = all(r['dentro'] for r in res) if res else None
        rows.append({'op': op, 'resultados': res, 'dentro_geral': dentro_geral})
        for r in res:
            if r['dentro']:
                meta_stats[r['meta']]['dentro'] += 1
            else:
                meta_stats[r['meta']]['fora'] += 1

    total = len(operations)
    dentro_count = sum(1 for r in rows if r['dentro_geral'])

    return render_template('sla_relatorio.html',
                           rows=rows,
                           total=total,
                           dentro_count=dentro_count,
                           meta_stats=dict(meta_stats),
                           date_from=date_from_str,
                           date_to=date_to_str,
                           sla_goals=sla_goals,
                           units=units,
                           locations=locations,
                           f_unit=f_unit,
                           f_location=f_location,
                           f_type=f_type)


@app.route('/sla-relatorio/export')
@login_required
def export_sla_relatorio():
    if not has_permission('relatorios'):
        return redirect(url_for('dashboard'))

    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    date_from_str = request.args.get('date_from', today_str)
    date_to_str   = request.args.get('date_to', today_str)

    query = LoadOperation.query.filter(LoadOperation.status == 'Finalizado')
    if date_from_str:
        try:
            query = query.filter(LoadOperation.end_time >= datetime.strptime(date_from_str, '%Y-%m-%d'))
        except ValueError:
            pass
    if date_to_str:
        try:
            dt_to = datetime.strptime(date_to_str, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(LoadOperation.end_time < dt_to)
        except ValueError:
            pass

    operations = query.all()
    sla_goals = SLAGoal.query.filter_by(active=True).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Relatório SLA'

    header_fill = PatternFill(start_color='0066CC', end_color='0066CC', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True)
    green_fill  = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
    red_fill    = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')

    base_headers = ['Nº Carregamento', 'Separador', 'Destino', 'Início', 'Fim', 'Duração (min)', 'SKUs', 'Peso (kg)', 'SLA Geral']
    meta_names = [g.name for g in sla_goals if g.metric != 'max_ocorrencias_dia']
    headers = base_headers + meta_names
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')

    for row_idx, op in enumerate(operations, 2):
        sla_results = {}
        for goal in sla_goals:
            try:
                if goal.metric == 'tempo_medio_sku' and op.sku_count:
                    v = op.duration_minutes / op.sku_count
                    sla_results[goal.name] = ('✓ Dentro' if v <= goal.target_value else '✗ Fora', v <= goal.target_value)
                elif goal.metric == 'tempo_medio_tonelada' and op.weight_kg:
                    v = op.duration_minutes / (op.weight_kg / 1000)
                    sla_results[goal.name] = ('✓ Dentro' if v <= goal.target_value else '✗ Fora', v <= goal.target_value)
                elif goal.metric == 'tempo_medio_carregamento':
                    v = op.duration_minutes
                    sla_results[goal.name] = ('✓ Dentro' if v <= goal.target_value else '✗ Fora', v <= goal.target_value)
                elif goal.metric == 'sku_por_hora' and op.duration_minutes:
                    v = (op.sku_count / op.duration_minutes) * 60
                    sla_results[goal.name] = ('✓ Dentro' if v >= goal.target_value else '✗ Fora', v >= goal.target_value)
            except (ZeroDivisionError, TypeError):
                pass

        geral_ok = all(v[1] for v in sla_results.values()) if sla_results else None
        sep = op.separator_1_name or ''
        if op.separator_2_name:
            sep += f' / {op.separator_2_name}'

        row_data = [
            op.load_number or '',
            sep,
            op.destination or '',
            op.start_time.strftime('%d/%m/%Y %H:%M') if op.start_time else '',
            op.end_time.strftime('%d/%m/%Y %H:%M') if op.end_time else '',
            op.duration_minutes or 0,
            op.sku_count or 0,
            op.weight_kg or 0,
            '✓ Dentro' if geral_ok else ('✗ Fora' if geral_ok is False else '-'),
        ]
        for mn in meta_names:
            row_data.append(sla_results.get(mn, ('-', None))[0])

        for col, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col, value=val)
            if col == 9:
                cell.fill = green_fill if geral_ok else (red_fill if geral_ok is False else PatternFill())
            elif col > 9:
                mn = meta_names[col - 10]
                r = sla_results.get(mn)
                if r:
                    cell.fill = green_fill if r[1] else red_fill

    for col in ws.columns:
        max_len = max((len(str(c.value or '')) for c in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name='relatorio_sla.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# ============= PAINEL DO DIA =============

@app.route('/painel')
def painel():
    hoje = datetime.utcnow().date()
    amanha = hoje + timedelta(days=1)
    operations = LoadOperation.query.filter(
        db.or_(
            db.and_(LoadOperation.start_time >= datetime(hoje.year, hoje.month, hoje.day),
                    LoadOperation.start_time < datetime(amanha.year, amanha.month, amanha.day)),
            db.and_(LoadOperation.created_date >= datetime(hoje.year, hoje.month, hoje.day),
                    LoadOperation.created_date < datetime(amanha.year, amanha.month, amanha.day),
                    LoadOperation.start_time == None)
        )
    ).order_by(LoadOperation.status, LoadOperation.start_time).all()

    total = len(operations)
    finalizados = sum(1 for op in operations if op.status == 'Finalizado')
    em_sep = sum(1 for op in operations if op.status == 'Em Andamento')
    nao_iniciados = sum(1 for op in operations if op.status == 'Não Iniciado')

    return render_template('painel.html',
                           operations=operations,
                           total=total,
                           finalizados=finalizados,
                           em_sep=em_sep,
                           nao_iniciados=nao_iniciados,
                           now=datetime.utcnow())


# ============= CRIAR BANCO =============

def init_db():
    with app.app_context():
        # Criar todas as tabelas
        db.create_all()
        
        # Migrar banco antigo se necessário
        try:
            inspector = inspect(db.engine)
            columns = [c['name'] for c in inspector.get_columns('user')]
            
            if 'status' not in columns:
                print("⚠️  Migrando banco antigo...")
                with db.engine.begin() as conn:
                    try:
                        conn.execute(db.text("ALTER TABLE user ADD COLUMN status VARCHAR(50) DEFAULT 'pending'"))
                    except:
                        pass
                    try:
                        conn.execute(db.text("ALTER TABLE user ADD COLUMN first_login BOOLEAN DEFAULT 1"))
                    except:
                        pass
                print("✅ Banco migrado com sucesso!")

            # Migrar novas colunas de agendamento e pausa
            lo_columns = [c['name'] for c in inspector.get_columns('load_operation')]
            new_cols = {
                'scheduled_date':      "ALTER TABLE load_operation ADD COLUMN scheduled_date DATETIME",
                'is_scheduled':        "ALTER TABLE load_operation ADD COLUMN is_scheduled BOOLEAN DEFAULT 0",
                'released_by':         "ALTER TABLE load_operation ADD COLUMN released_by VARCHAR(120)",
                'released_at':         "ALTER TABLE load_operation ADD COLUMN released_at DATETIME",
                'paused_at':           "ALTER TABLE load_operation ADD COLUMN paused_at DATETIME",
                'pause_reason':        "ALTER TABLE load_operation ADD COLUMN pause_reason VARCHAR(200)",
                'paused_by':           "ALTER TABLE load_operation ADD COLUMN paused_by VARCHAR(120)",
                'total_pause_minutes': "ALTER TABLE load_operation ADD COLUMN total_pause_minutes INTEGER DEFAULT 0",
            }
            with db.engine.begin() as conn:
                for col, sql in new_cols.items():
                    if col not in lo_columns:
                        try:
                            conn.execute(db.text(sql))
                            print(f"✅ Coluna '{col}' adicionada")
                        except:
                            pass
        except Exception as e:
            print(f"ℹ️  Banco novo sendo criado...")
        
        # Criar admin se não existir
        try:
            if not User.query.filter_by(email='admin@sistema').first():
                admin = User(email='admin@sistema', full_name='Admin Sistema', role='admin', status='approved', first_login=False)
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("✅ Admin criado: admin@sistema / admin123")
        except Exception as e:
            db.session.rollback()
            print(f"✅ Admin já existe")
        
        # Criar permissões padrão
        try:
            if RolePermission.query.first() is None:
                pages = ['dashboard', 'operation', 'cadastros', 'relatorios', 'ocorrencias', 'sla', 'metas_sla', 'usuarios']
                
                for page in pages:
                    perm = RolePermission(role='admin', permission=page)
                    db.session.add(perm)
                
                for page in ['operation', 'cadastros', 'relatorios', 'ocorrencias', 'sla']:
                    perm = RolePermission(role='supervisor', permission=page)
                    db.session.add(perm)
                
                perm = RolePermission(role='executor', permission='operation')
                db.session.add(perm)
                
                db.session.commit()
                print("✅ Permissões padrão criadas")
        except Exception as e:
            db.session.rollback()
            print(f"✅ Permissões já existem")
        
        # Config
        try:
            if not AppConfig.query.first():
                config = AppConfig(app_name='Monitor de Separação', primary_color='#0066CC', secondary_color='#1aa84a')
                db.session.add(config)
                
                sla_metas = [
                    SLAGoal(name='Tempo Médio por SKU', metric='tempo_medio_sku', target_value=2.0, unit='min', active=True),
                    SLAGoal(name='Tempo Médio por Tonelada', metric='tempo_medio_tonelada', target_value=5.0, unit='min', active=True),
                    SLAGoal(name='Tempo Médio por Carregamento', metric='tempo_medio_carregamento', target_value=40.0, unit='min', active=True),
                    SLAGoal(name='Máx. Ocorrências por Dia', metric='max_ocorrencias_dia', target_value=5.0, unit='qtd', active=True),
                    SLAGoal(name='SKU por Hora', metric='sku_por_hora', target_value=60.0, unit='SKU/h', active=True),
                ]
                for meta in sla_metas:
                    db.session.add(meta)
                
                db.session.commit()
                print("✅ Configurações e metas SLA criadas")
        except Exception as e:
            db.session.rollback()
            print(f"✅ Configurações já existem")

# ============= HELPERS E CONTEXT =============

def get_app_config():
    """Retorna configuração do app ou padrão"""
    config = AppConfig.query.first()
    if not config:
        config = AppConfig(
            app_name='LogTrack',
            app_description='Monitor de Separação',
            primary_color='#0066CC',
            secondary_color='#1aa84a'
        )
        db.session.add(config)
        db.session.commit()
    return config

@app.context_processor
def inject_config():
    """Injeta config em TODOS os templates automaticamente"""
    config = get_app_config()
    return dict(
        config=config,
        primary_color=config.primary_color,
        secondary_color=config.secondary_color
    )

# ============= CONFIGURAÇÕES =============

@app.route('/configuracoes')
@login_required
def configuracoes():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    
    config = AppConfig.query.first()
    return render_template('configuracoes.html', config=config)

@app.route('/configuracoes/update', methods=['POST'])
@login_required
def update_configuracoes():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    try:
        config = AppConfig.query.first()
        if not config:
            config = AppConfig()
            db.session.add(config)
        
        config.app_name = request.form.get('app_name', 'LogTrack')
        config.app_description = request.form.get('app_description', '')
        config.primary_color = request.form.get('primary_color', '#0066CC')
        config.secondary_color = request.form.get('secondary_color', '#1aa84a')
        
        # Processar upload de logo
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                config.logo_filename = filename
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro em update_configuracoes: {e}")
    return redirect(url_for('configuracoes'))

# ============= PWA - PROGRESSIVE WEB APP =============

@app.route('/manifest.json')
def manifest():
    """Retorna o manifest.json do PWA"""
    return jsonify({
        "name": "LogTrack - Monitor de Separação",
        "short_name": "LogTrack",
        "description": "Automação inteligente de operações de picking com dashboards em tempo real",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#0066CC",
        "orientation": "portrait-primary",
        "scope": "/",
        "icons": [
            {
                "src": "/static/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any"
            },
            {
                "src": "/static/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any"
            }
        ],
        "categories": ["productivity", "business"],
        "screenshots": [
            {
                "src": "/static/screenshot-540.png",
                "sizes": "540x720",
                "type": "image/png"
            }
        ]
    })

@app.route('/service-worker')
def service_worker():
    """Service Worker desabilitado - causava erros com extensões do Chrome"""
    return '', 204  # No Content

# ============= API DASHBOARD DINÂMICO =============

@app.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    """API que retorna estatísticas para o dashboard em tempo real"""
    try:
        date_from      = request.args.get('date_from')
        date_to        = request.args.get('date_to')
        unit_id        = request.args.get('unit')
        location_id    = request.args.get('location')
        operation_type = request.args.get('operation_type')

        query = LoadOperation.query.filter(
            LoadOperation.status.in_(['Finalizado', 'finalizado', 'FINALIZADO'])
        )

        if date_from:
            try:
                query = query.filter(LoadOperation.start_time >= datetime.strptime(date_from, '%Y-%m-%d'))
            except: pass

        if date_to:
            try:
                dt = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(LoadOperation.start_time <= dt)
            except: pass

        if unit_id and unit_id != '':
            try:
                query = query.filter(LoadOperation.unit_id == int(unit_id))
            except: pass

        if location_id and location_id != '':
            try:
                query = query.filter(LoadOperation.location_id == int(location_id))
            except: pass

        if operation_type and operation_type != '':
            try:
                query = query.filter(LoadOperation.operation_type == operation_type)
            except: pass

        operations = query.all()
        print(f"🔍 API Dashboard: {len(operations)} operações finalizadas")

        # Colaboradores — cada membro da dupla contabilizado individualmente
        collaborators_dict = {}

        def _add_to_collab(name, op, is_dupla):
            if not name:
                return
            if name not in collaborators_dict:
                collaborators_dict[name] = {
                    'name': name,
                    'loads_solo':  0,   # operações individuais
                    'loads_dupla': 0,   # operações em dupla
                    'loads':       0,   # total
                    'skus':        0,
                    'total_time':  0,
                    'weight':      0,
                    'time_per_load': 0,
                    'time_per_sku':  0,
                    'sku_per_hour':  0,
                }
            c = collaborators_dict[name]
            c['loads'] += 1
            if is_dupla:
                c['loads_dupla'] += 1
                # Em dupla: SKU e tempo divididos igualmente entre os dois
                c['skus']       += (op.sku_count or 0) / 2
                c['weight']     += (op.weight_kg or 0) / 2
                c['total_time'] += (op.duration_minutes or 0)   # tempo total igual pra ambos
            else:
                c['loads_solo'] += 1
                c['skus']       += op.sku_count or 0
                c['weight']     += op.weight_kg or 0
                c['total_time'] += op.duration_minutes or 0

        for op in operations:
            try:
                is_dupla = bool(op.separator_2_name)
                _add_to_collab(op.separator_1_name, op, is_dupla)
                if is_dupla:
                    _add_to_collab(op.separator_2_name, op, is_dupla)
            except: continue

        for c in collaborators_dict.values():
            skus_int = int(c['skus'])   # arredondar após soma
            c['skus'] = skus_int
            if c['loads']      > 0: c['time_per_load'] = c['total_time'] / c['loads']
            if skus_int        > 0: c['time_per_sku']  = c['total_time'] / skus_int
            if c['total_time'] > 0: c['sku_per_hour']  = (skus_int * 60) / c['total_time']

        # Tipos de operação
        operation_types = {}
        for op in operations:
            t = op.operation_type or 'Desconhecido'
            if t not in operation_types:
                operation_types[t] = {'type': t, 'skus': 0, 'time': 0, 'loads': 0}
            operation_types[t]['skus']  += op.sku_count or 0
            operation_types[t]['loads'] += 1
            operation_types[t]['time']  += op.duration_minutes or 0

        # KPIs
        total_skus   = sum(op.sku_count or 0        for op in operations)
        total_time   = sum(op.duration_minutes or 0 for op in operations)
        total_weight = sum(op.weight_kg or 0        for op in operations)
        total_loads  = len(operations)

        avg_per_sku  = total_time / total_skus   if total_skus   > 0 else 0
        avg_per_load = total_time / total_loads  if total_loads  > 0 else 0

        # ✅ Tempo Médio/Ton: considera SOMENTE operações com peso informado (weight_kg > 0),
        # para que cargas sem peso registrado não distorçam a média.
        ops_com_peso        = [op for op in operations if (op.weight_kg or 0) > 0]
        tempo_ops_com_peso  = sum(op.duration_minutes or 0 for op in ops_com_peso)
        peso_ops_com_peso   = sum(op.weight_kg or 0        for op in ops_com_peso)
        avg_per_ton = (tempo_ops_com_peso / (peso_ops_com_peso / 1000)) if peso_ops_com_peso > 0 else 0

        occurrences = 0
        try:
            if operations:
                occurrences = Occurrence.query.filter(
                    Occurrence.load_operation_id.in_([op.id for op in operations])
                ).count()
        except:
            occurrences = sum(op.occurrence_count or 0 for op in operations)

        return jsonify({
            'collaborators':   list(collaborators_dict.values()),
            'operation_types': list(operation_types.values()),
            'kpis': {
                'avg_time_per_sku':  float(avg_per_sku),
                'avg_time_per_ton':  float(avg_per_ton),
                'avg_time_per_load': float(avg_per_load),
                'total_skus':    int(total_skus),
                'total_weight':  float(total_weight),
                'total_loads':   int(total_loads),
                'occurrences':   int(occurrences)
            }
        })

    except Exception as e:
        print(f"❌ ERRO API Dashboard: {e}")
        import traceback; traceback.print_exc()
        return jsonify({
            'error': str(e), 'collaborators': [], 'operation_types': [],
            'kpis': {'avg_time_per_sku': 0, 'avg_time_per_ton': 0, 'avg_time_per_load': 0,
                     'total_skus': 0, 'total_weight': 0, 'total_loads': 0, 'occurrences': 0}
        }), 500

# ============= MAIN =============

init_db()

if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║                                                                ║
    ║        🚀 Monitor de Separação iniciando...                  ║
    ║        📍 Acesso: http://localhost:3000                      ║
    ║        👤 Admin padrão: admin@sistema                        ║
    ║        🔑 Senha: admin123                                    ║
    ║                                                                ║
    ║        ✅ Sistema completo com autenticação!                 ║
    ║                                                                ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    app.run(debug=False, host='0.0.0.0', port=3000)
