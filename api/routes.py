from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import requests
import logging
from datetime import datetime
from flask import Flask, request, jsonify, session, redirect, url_for
from login_required import login_required
from phone_validation import IPQS
import json
from pymongo_get_database import get_database
import os
from dotenv import load_dotenv



app = Flask(__name__)
load_dotenv()
app.secret_key = os.getenv("APP_SECRET_KEY")


dbname = get_database()
users_collection = dbname["user"]

# Combined endpoint for user signup and login
@app.route('/signup_login', methods=['POST'])
def signup_login():
    data = request.json
    username = data.get('username')
    phone = data.get('phone')

    if not username:
        return jsonify({'error': 'Username is required'}), 400

    user = users_collection.find_one({'username': username})

    if user:
        # If user already exists, perform login
        
            session['user_id'] = user['user_id']
            return jsonify({'message': 'Login successful', 'user_id': user['user_id']}), 200
       
    else:
        # If user does not exist, perform signup and login
        
        user_id = str(uuid.uuid4())

        users_collection.insert_one({
            'user_id': user_id,
            'username': username,
            'phone': phone,
            'reports': [],
            'feedback': [],
            'created_at': datetime.now()
        })

        session['user_id'] = user_id
        return jsonify({'message': 'User signed up and logged in successfully', 'user_id': user_id}), 201



# Endpoint for user profile
@app.route('/profile/<user_id>', methods=['GET'])
@login_required
def profile(user_id):
    user = users_collection.find_one({'user_id': user_id}, {'_id': 0, 'password': 0})

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(user), 200


#Endpoint to update user profile
@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    data = request.json
    phone = data.get('phone')
    username = data.get('username')
    user_id = session['user_id']

    user = users_collection.find_one({'user_id': user_id})

    if not user:
        return jsonify({'error': 'User not found'}), 404
    try:
        users_collection.update_one({'user_id': user_id}, {'$set': {'phone': phone}})
        users_collection.update_one({'user_id': user_id}, {'$set': {'username': username}})
    except Exception as e:
        return jsonify({'error': 'Internal Server Error'}), 500
    return jsonify({'message': 'Profile updated successfully'}), 200


# Endpoint for user logout
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'User logged out successfully'}), 200

# Endpoint to receive incoming SMS
@app.route('/check_sms', methods=['POST'])
@login_required
def check_sms():
    data = request.json
    sms_content = data.get('data')
    user_id = session['user_id']

    # Capture the time when the SMS is received
    received_time = datetime.now()

    # Log the SMS content
    print("Received SMS content: %s", sms_content)

    # Send SMS content to AI model API
    ai_model_url = 'https://harisshragav.ap-south-1.modelbit.com/v1/predict/latest'
    try:
        response = requests.post(ai_model_url, json={'data': sms_content})
        response.raise_for_status()  # Raise an exception for HTTP errors
        result = response.json().get('data')
        #logging.info("AI model response: %s", result)

        #calculate time when the message was received and the report was generated
        report_generated_time = datetime.now()

        users_collection.update_one({'user_id': user_id}, {'$push': {'reports': {
            'message_id': str(uuid.uuid4()),
            'message_type': 'sms',
            'message': sms_content,
            'report': result,
            'received_time': received_time,
            'report_generated_time': report_generated_time
        }}})


        return result
    except Exception as e:
        #logging.error("Error processing SMS content: %s", e)
        return jsonify({'error': 'Internal Server Error'}), 500

#Endpoint to check urls
@app.route('/check_url', methods=['POST'])
@login_required
def check_url():
    data = request.json
    url = data.get('url')
    user_id = session['user_id']

    # Capture the time when the SMS is received
    received_time = datetime.now()

    # Send URL to AI model API
    ai_model_url = 'https://jithinshaji.ap-south-1.modelbit.com/v1/predict_malicious_url/latest'
    try:
        response = requests.post(ai_model_url, json={'data': url})
        response.raise_for_status()  # Raise an exception for HTTP errors
        result = response.json().get('data')

        if result == 1:
            result = "Malicious"
        else:
            result = "Safe"

        final_result = {
            'predict': result
        }

        #calculate time when the message was received and the report was generated
        report_generated_time = datetime.now()

        print(response)


        # Process response from AI model API
        users_collection.update_one({'user_id': user_id}, {'$push': {'reports': {
                'message_id': str(uuid.uuid4()),
                'message_type': 'url',
                'message': url,
                'report': final_result,
                'received_time': received_time,
                'report_generated_time': report_generated_time
            }}})
        
        # Return result
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': 'Internal Server Error'}), 500

    

# Enpoint to check phone numbers
@app.route('/check_phone', methods=['POST'])
@login_required
def check_phone():
    data = request.json
    phone_number = data.get('phone_number')
    user_id = session['user_id']

    countries = {'US', 'CA', 'IN', 'GB', 'AU'}
    # Custom fields
    additional_params = {
        'country': countries
    }

    ipqs = IPQS()
    try:
        result = ipqs.phone_number_api(phone_number, additional_params)

        # Check to see if our query was successful.
        if 'success' in result and result['success']:

            #Save the report in the database
            users_collection.update_one({'user_id': user_id}, {'$push': {'reports': {
                'message_id': str(uuid.uuid4()),
                'message_type': 'phone',
                'message': phone_number,
                'report': result,
                'received_time': datetime.now(),
                'report_generated_time': datetime.now()
            }}})

            # Extract relevant information from the response
            return jsonify(result)
        
        else:
            return jsonify({'error': 'Phone Number Validation Failed'}), 400
    except Exception as e:
        return jsonify({'error': 'Internal Server Error'}), 500


#Endpoint to report phone numbers
@app.route('/report_phone', methods=['POST'])
@login_required
def report_phone():
    data = request.json
    phone_number = data.get('phone_number')
    country = data.get('country')
    user_id = session['user_id']

    ipqs = IPQS()
    try:
        result = ipqs.report_phonenumber_api(phone_number, country)

        # Check to see if our query was successful.
        
            # Save the report in the database
            # Extract relevant information from the response
        return jsonify(result), 200
        
    
    except Exception as e:
        return jsonify({'error': 'Internal Server Error'}), 500


#Endpoint to provide feedback
@app.route('/feedback', methods=['POST'])
@login_required
def feedback():
    data = request.json
    feedback = data.get('feedback')
    user_id = session['user_id']

    try:
        # Save the feedback in the database
        users_collection.update_one({'user_id': user_id}, {'$push': {'feedback': {
            'feedback_id': str(uuid.uuid4()),
            'feedback': feedback,
            'created_at': datetime.now()
        }}})
    except Exception as e:
        return jsonify({'error': 'Error while updating database'}), 400

    return jsonify({'message': 'Feedback submitted successfully'}), 200


if __name__ == '__main__':
    app.run(debug=True, port=3000)

