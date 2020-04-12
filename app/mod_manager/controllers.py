# Import flask dependencies
from flask import Blueprint, request, render_template, \
                  flash, g, session, redirect, url_for, abort

from markupsafe import escape 

# Import password / encryption helper tools
from werkzeug.security import check_password_hash, generate_password_hash

# import checked_logged_in function
from app.mod_auth.controllers import check_logged_in

# Import the database object from the main app module
from app import db

# Import User model for manager and gardener
from app.mod_auth.models import User
# Import employeeInfo model for Manager and gardener
from app.mod_owner.models import employeeInfo, nurseryStaff

from app.mod_manager.models import plantTypeInfo, plantImages, plantTypeDescription, plantTypeUses

from app.mod_gardener.models import seedTypeInfo

from app.mod_manager.queries import get_gardeners

from app.mod_gardener.queries import get_complete_plant_description

# Import module forms
from app.mod_auth.forms import LoginForm

# Import module models (i.e. User)
from app.mod_auth.models import User
# For image upload making directory
from pathlib import Path

# For uploading image
from werkzeug.utils import secure_filename

# For creating image paths
import os
# For editing Images
from PIL import Image
from io import BytesIO

# Base directory to store images
from config import BASE_IMG_DIR

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


# Define the blueprint: 'auth', set its url prefix: app.url/auth
mod_manager = Blueprint('manager', __name__, url_prefix='/')

@mod_manager.route('/', methods=['GET'])
def index():
    if check_logged_in(session['role']):
        return redirect(url_for('landing.index'))
    else:
        return redirect(url_for('landing.index'))

@mod_manager.route('/add_gardener', methods=['GET', 'POST'])
def add_gardener():
    if check_logged_in(2):

        nID = nurseryStaff.query.filter_by(eID=session['user_id']).first()
        if nID != None:
            nID = nID.nID
    
        if request.method == 'POST' and nID != None:
            username = request.form['name']
            emailID = request.form['emailID']
            password = request.form['password']
            role = 3
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
                db.session.add(nurseryStaff(nID, temp.id))
                db.session.commit()
                return redirect(url_for('manager.index'))
        if nID != None:
            return render_template('manager/add_gardener.html', role=str(session['role']), assigned='True')
        return render_template('manager/not_assigned.html', role=str(session['role']))
    return redirect(url_for('landing.index'))

@mod_manager.route('view_gardeners', methods=['GET'])
def view_gardeners():
    if check_logged_in(2):
        nID = nurseryStaff.query.filter_by(eID=session['user_id']).first()
        if nID != None:
            nID = nID.nID
            gardener_list = get_gardeners(nID)
            
            if gardener_list == []:
                gardener_list = [('', '', ''),]
            return render_template("manager/view_gardeners.html", role = str(session['role']), employee_list = gardener_list)
        return render_template('manager/not_assigned.html', role=str(session['role']))
    return redirect(url_for('landing.index'))

# Helper function for uploaded Images
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@mod_manager.route('/add_plant', methods=['GET', 'POST'])
def add_plant():
    if check_logged_in(2):
        nID = nurseryStaff.query.filter_by(eID=session['user_id']).first()
        
        if request.method == 'POST' and nID != None:
            nID = nID.nID
            plantName = request.form['pname'].lower()
            fertilizer = request.form['fertilizer'].lower()
            weather = request.form['weather'].lower()
            water = int(request.form['water'])
            sunlight = request.form['sunlight'].lower()
            potsize = request.form['potsize'].lower()
            special = request.form['special'].lower()
            uses = request.form.getlist('uses')

            cosmetic    = False
            medicinal   = False
            decorative  = False
            edible      = False

            for use in uses:
                if 'cosmetic' == use:
                    cosmetic = True
                elif 'medicinal' == use:
                    medicinal = True
                elif 'decorative' == use:
                    decorative = True
                elif 'edible' == use:
                    edible = True
            
            if special == None:
                special = 'None'

            if plantTypeInfo.query.filter_by(plantTypeName=plantName, nID=nID).first() is not None:
                return redirect(url_for('landing.index'))

            plant = plantTypeInfo(plantName, nID)
            db.session.add(plant)
            db.session.commit()

            db.session.add(seedTypeInfo(plant.plantTypeID))
            db.session.commit()

            description = plantTypeDescription(plant.plantTypeID, fertilizer, weather, sunlight, water, potsize, special)
            db.session.add(description)
            db.session.commit()

            plantUses = plantTypeUses(plant.plantTypeID, cosmetic, medicinal, decorative, edible)
            db.session.add(plantUses)
            db.session.commit()

            if 'img' not in request.files:
                return redirect(url_for('landing.index'))
            
            file = request.files['img']

            if file.filename == '':
                return redirect(url_for('landing.index'))

            plantType = plantTypeInfo.query.filter_by(plantTypeName=plantName, nID=nID).first()
            
            IMG_DIR = os.path.join(BASE_IMG_DIR, 'plants/{nID}/{typeID}'.format(nID=nID, typeID=plantType.plantTypeID))

            Path(IMG_DIR).mkdir(parents=True, exist_ok=True)

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                IMG_PATH = os.path.join(IMG_DIR, plantName+'.'+filename.rsplit('.')[1].lower())
                
                img = Image.open(BytesIO(file.read()))
                img = img.resize((250, 200))
                img.save(IMG_PATH)
                
                IMG_PATH = 'static/'+IMG_PATH.split('static/')[1]
                db.session.add(plantImages(plantType.plantTypeID, IMG_PATH))
                db.session.commit()
                return redirect(url_for('landing.index'))
        
        if nID != None:
            nID = nID.nID
            return render_template('manager/add_plant.html', role=str(session['role']), assigned='True')
        return render_template('manager/not_assigned.html', role=str(session['role']))
    return redirect(url_for('landing.index'))

@mod_manager.route('/view_plants', methods=['GET'])
def view_plants():
    if check_logged_in(2):
        nID = nurseryStaff.query.filter_by(eID=session['user_id']).first()

        if nID != None:
            nID = nID.nID
            plant_type_list = plantTypeInfo.query.filter_by(nID=nID).all()
            plant_description_list = []
            for plant in plant_type_list:
                plant_description = get_complete_plant_description(plant.plantTypeID)
                plant_description_list.append(plant_description)
            return render_template('manager/view_plants.html', role=str(session['role']), plant_type_list=plant_description_list)

        return render_template('manager/not_assigned.html', role=str(session['role']))

    return redirect(url_for('landing.index'))