# Import flask dependencies
from flask import Blueprint, request, render_template, \
                  flash, g, session, redirect, url_for, \
                  abort
# Import db from app
from app import db

# Import User model for manager and gardener
from app.mod_auth.models import User
# Import employeeInfo model for Manager and gardener
from app.mod_owner.models import employeeInfo, nurseryInfo,\
     nurseryAddress, nurseryStaff

from markupsafe import escape

# Function to get employee list from database
from app.mod_owner.queries import get_employee_list, get_nurser_list,\
    check_manager_assigned, get_manager_id, get_stats_for_maintenance_cost, get_stats_for_sales

# Import password / encryption helper tools
from werkzeug.security import check_password_hash, generate_password_hash

# import checked_logged_in function
from app.mod_auth.controllers import check_logged_in

from app.mod_owner.forms import registerNurseryForm, RegisterWorker

# Define the blueprint: 'customer', set its url prefix: app.url/auth
mod_owner = Blueprint('owner', __name__, url_prefix='/')


@mod_owner.route('/welcome_owner', methods=['GET'])
def index():
    if check_logged_in(session['role']):
        IMG_PATH = get_stats_for_maintenance_cost(session['user_id'])
        return render_template('landing/index.html', role=str(session['role']), maintenance_img=IMG_PATH)
    else:
        return redirect(url_for('landing.index'))

@mod_owner.route('/add_manager', methods=['GET', 'POST'])
def add_manager():
    print(check_logged_in(1))
    if check_logged_in(1):
        form = RegisterWorker(request.form)
        if request.method == 'POST' and form.validate():
            username = form.name.data
            emailID = form.email.data
            password = form.password.data
            role = 2
            error = None

            if not username:
                error = 'Username is required.'
            elif not password:
                error = 'Password is required.'
            elif User.query.filter_by(emailID = emailID
            ).first() is not None:
                error = 'User {} is already registered.'.format(username)
            if error is None:
                temp = User(username, emailID, generate_password_hash(password), role)
                db.session.add(temp)
                db.session.commit()
                db.session.add(employeeInfo(temp.id , int(session['user_id'])))
                db.session.commit()
                return redirect(url_for('owner.index'))

        return render_template('owner/add_employee.html',form = form,title = "Add Manager Page", role = str(session['role']))
    return redirect(url_for('landing.index'))

# YET TO ADD FILTERS: nurserty, salary, date, performance
@mod_owner.route('/view_employees', methods=['GET'])
def view_employees():
    if check_logged_in(1):
        
        designation = request.args.get('role', default = '')
        order = request.args.get('order', default='')
        status = request.args.get('status', default='')

        employee_list = get_employee_list(session['user_id'], status)
        
        temp = []
        if designation != '' and escape(designation.lower()) in ['gardener', 'manager']:
            for e in employee_list:
                if e[2].lower() == escape(designation.lower()):
                    temp.append(e)
            employee_list = temp
        
        if employee_list == []:
            employee_list.append(('', '', ''))
        
        # Filter for ascending order
        if order == 'asc':
            return render_template('owner/view_employee.html', role=str(session['role']), employee_list=sorted(employee_list, key=lambda x:x[0]))
        # Filter for descending order
        if order == 'desc':
            return render_template('owner/view_employee.html', role=str(session['role']), employee_list=sorted(employee_list, key=lambda x:x[0])[::-1])
        
        return render_template('owner/view_employee.html', role = str(session['role']), employee_list = employee_list)
    return redirect(url_for('landing.index'))

# Add a new nursery
@mod_owner.route('/add_nursery', methods=['GET', 'POST'])
def add_nursery():
    if check_logged_in(1):
        form = registerNurseryForm(request.form)
        if request.method == 'POST' and form.validate():
            
            pincode     = form.pincode.data
            city        = form.city.data
            country     = form.country.data
            labour      = form.labour.data
            maintenance = form.maintenance.data
            if pincode != None or city != None or country != None or labour != None or maintenance != None:
                temp = nurseryInfo(ownerID=int(session['user_id']), maintenanceCost=maintenance, labourCost=labour)
                db.session.add(temp)
                db.session.commit()
                db.session.add(nurseryAddress(nID=temp.nID, pincode=pincode, city=city, country=country))
                db.session.commit()
            return redirect(url_for('owner.view_nurseries'))

        return render_template('owner/add_nursery.html', role = str(session['role']), form=form)
    return redirect(url_for('landing.index'))

# YET TO ADD FILTERS
@mod_owner.route('/view_nurseries', methods=['GET'])
def view_nurseries():
    if(check_logged_in(1)):
        return render_template('owner/view_nursery.html', role=str(session['role']), nursery_list=get_nurser_list(session['user_id']))
        
    return redirect(url_for('landing.index'))

# Assign manager to nurseries
@mod_owner.route('/view_nurseries/<int:id>/assign_manager', methods=['GET', 'POST'])
def assign_manager(id):
    if check_logged_in(1):
        if request.method == 'POST':
            
            managerEmailID = request.form['assign_manager']
            nID = id
            managerID = User.query.filter_by(emailID=managerEmailID).first().id
            db.session.add(nurseryStaff(nID, managerID))
            db.session.commit()
            return redirect(url_for('owner.view_nurseries'))

        # IF GET request, render page for assigning manager
        # Checks if manager is not already assigned
        if check_manager_assigned(id):
            return render_template('owner/assign_manager.html', role = str(session['role']), assigned='True')
        
        employee_list = get_employee_list(session['user_id'])
        designation = 'manager'
        
        temp = []
        for e in employee_list:
            if e[2].lower() == escape(designation.lower()) and nurseryStaff.query.filter_by( eID=User.query.filter_by(emailID=e[1]).first().id ).first() == None:
                temp.append(e)
        employee_list = temp
        if employee_list == []:
            employee_list.append(('', '', ''))
        return render_template('owner/assign_manager.html', role = str(session['role']), employee_list = employee_list, id=id)
    return redirect(url_for('landing.index'))

# Removes manager
@mod_owner.route('/view_nurseries/<int:id>/remove_manager', methods=['GET'])
def remove_manager(id):
    if check_logged_in(1):
        if check_manager_assigned(id):
            db.session.delete(nurseryStaff.query.filter_by(nID=id, eID=get_manager_id(id)).first())
            db.session.commit()
            return redirect(url_for('owner.view_nurseries'))
    return redirect(url_for('landing.index'))

# Cascades on delete
@mod_owner.route('/view_nurseries/<int:id>/remove_nursery')
def remove_nursery(id):
    if check_logged_in(1):
        db.session.delete(nurseryInfo.query.filter_by(nID=id).first())
        db.session.commit()
        return redirect(url_for('owner.view_nurseries'))
    return redirect(url_for('landing.index'))

@mod_owner.route('/view_stats_owner', methods=['GET'])
def view_stats():
    if check_logged_in(1):
        img_sales_stats = get_stats_for_sales(session['user_id'])
        return render_template('owner/stats.html', role=str(session['role']), img_sales_stats=img_sales_stats)
    return redirect('landing.index')