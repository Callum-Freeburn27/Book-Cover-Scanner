from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from flask_navigation import Navigation
import os
from booksDatabase import db, BooksPredictions, BooksInformation
from genre_model import GenreModel
from googleAPI import get_book_details_from_google
from ocr_feature import MainOCR

# configure the 2 models
genremodel = GenreModel()
infomodel = MainOCR()

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
UPLOAD_FOLDER = './static/'

# example info for homepage
exampleBookGenrePredictions = {}
exampleBookGenrePredictions['Confidence'] = '0.6679179'
exampleBookGenrePredictions['FileName'] = 'why_nations_fail.jpg'
exampleBookGenrePredictions['Genre'] = 'Business & Money'

exampleBookInfoPredictions = {}
exampleBookInfoPredictions['Title'] = 'Why Nations Fail'
exampleBookInfoPredictions['Author'] = ' Daron Acemoglu and James Robinson'
exampleBookInfoPredictions['Genre'] = 'Economics'
exampleBookInfoPredictions['Publisher'] = 'Crown Business'
exampleBookInfoPredictions['FileName'] = 'example_image_homepage.jpg'
exampleBookInfoPredictions['InfoLink'] = 'https://play.google.com/store/books/details?id=PLlOCUIAh88C&source=gbs_api'

# configure the app
app = Flask(__name__)
app.config ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///BooksPredictions.sqlite3'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'jwdjsjfnjsdfjasdfojkadsnfjadjfnasdfjfgndfsgkjfadgjadfngnadfj'    
db.init_app(app)
nav = Navigation(app)
with app.app_context():
    db.create_all()
    
# nav bar configure
nav.Bar('top', [
    nav.Item('Home', 'home_page'),
    nav.Item('Upload Book Cover', 'upload_cover'),
    nav.Item('Show Books Genre Pred Database', 'show_all_genre_pred', {'page': 1}),
    nav.Item('Show Books Info Pred Database', 'show_all_book_info', {'page': 1}),
    nav.Item('About Us', 'about_us'),
])

#function to check file type
def allowed_file(filename):     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# home page 
@app.route('/')
def home_page():
    return render_template('homepage.html', image = 'static/example_image_homepage.jpg', exampleBookGenrePredictions=exampleBookGenrePredictions,
                           exampleBookInfoPredictions = exampleBookInfoPredictions)

# upload image and run through models    
@app.route('/uploadImage', methods=['POST', 'GET'])
def upload_cover():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(url_for('upload_cover'))
        file = request.files['file']
        if file and not allowed_file(file.filename):
            flash('Not a Valid File, must be a png, jpg or jpeg', 'error')
            return redirect(url_for('upload_cover'))
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # genre predict model
            genre, confidence = genremodel.predict_genre('static/' + filename)
            session['book_genre_predictions'] = {'Genre': genre, 'Confidence':str(confidence), 'File Name':filename}
            # ocr model prediction
            session['book_info_predictions'] = infomodel.OCR('static/' + filename)
            session['book_info_predictions']['FileName'] = filename
            
        return redirect(url_for('check_book_details'))
    return render_template('uploadCover.html')

# after model predictions have been generated, redirect to this page for confimation
@app.route('/checkbookDetails', methods=['POST', 'GET'])
def check_book_details():
    book_info_predictions = session['book_info_predictions']
    book_info_predictions = get_book_details_from_google(book_info_predictions['predTitle'], book_info_predictions['predAuthor'])
    book_info_predictions['FileName'] = session['book_info_predictions']['FileName']
    
    book_genre_predictions=session['book_genre_predictions']
    
    if request.method == 'POST':
        # if predictions are correct user will select yes and will  be saved in database
        if request.form['confirm_details_button'] == 'Yes':
            
            #submit to databases
            commitBookInfoPred = BooksInformation(book_info_predictions['Title'], book_info_predictions['Authors'], book_info_predictions['Categories'], book_info_predictions['Publisher'], \
             book_info_predictions['FileName'], book_info_predictions['InfoLink'])
            db.session.add(commitBookInfoPred)
            db.session.commit()

            commitBookGenrePred = BooksPredictions(book_genre_predictions['Genre'], book_genre_predictions['Confidence'], book_genre_predictions['File Name'])
            db.session.add(commitBookGenrePred)
            db.session.commit()
            
            # once saved redirect back to upload image
            return redirect(url_for('upload_cover'))
        elif request.form['confirm_details_button'] == 'No': 
            return redirect(url_for('edit_book_details'))
        else:
            pass
    return render_template('check_book_details.html', book_genre_predictions = book_genre_predictions, image = 'static/' + book_genre_predictions['File Name'], book_info_predictions = book_info_predictions)

# if user says the predictions are incorrect then redirect here to enter in correct information and save to database
@app.route('/editbookDetails', methods=['POST', 'GET'])
def edit_book_details():
    book_info_predictions = session['book_info_predictions']
    book_genre_predictions = session['book_genre_predictions']
    
    if request.method == 'POST':
        # display results and save to databases
        searchTitle = request.form["updatedbooktitle"]
        searchAuthor = request.form["updatedbookauthor"]
        book_info_predictions = get_book_details_from_google(searchTitle, searchAuthor)
        book_info_predictions['FileName'] = session['book_info_predictions']['FileName']

        commitBookInfoPred = BooksInformation(book_info_predictions['Title'], book_info_predictions['Authors'], book_info_predictions['Categories'], book_info_predictions['Publisher'], \
             book_info_predictions['FileName'], book_info_predictions['InfoLink'])
        db.session.add(commitBookInfoPred)
        db.session.commit()

        commitBookGenrePred = BooksPredictions(book_genre_predictions['Genre'], book_genre_predictions['Confidence'], book_genre_predictions['File Name'])
        db.session.add(commitBookGenrePred)
        db.session.commit()
        
        # once finished redirect to upload another
        return redirect(url_for('upload_cover'))
    return render_template('edit_book_details.html', book_genre_predictions = book_genre_predictions, image = 'static/' + book_genre_predictions['File Name'], book_info_predictions = book_info_predictions)


# get all genre predictions
@app.route('/show_all_genre_pred')
def show_all_genre_pred():
   return render_template('show_all_genre_pred.html', GenreBookPredictions = BooksPredictions.query.all())

# get all info predictions
@app.route('/show_all_book_info')
def show_all_book_info():
   return render_template('show_all_book_info.html', GenreInfoPredictions = BooksInformation.query.all())

# about us page
@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

if __name__ == '__main__':
    app.run(debug=True)