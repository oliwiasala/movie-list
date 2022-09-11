from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import FloatField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange
import requests
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
Bootstrap(app)

API_URL = 'https://api.themoviedb.org/3'
API_KEY = os.getenv('API_KEY')


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(250), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String, nullable=False)
    rating = db.Column(db.Float, nullable=True)
    ranking = db.Column(db.Integer, nullable=False)
    review = db.Column(db.String, nullable=True)
    img_url = db.Column(db.String, nullable=False)


db.create_all()


class AddMovie(FlaskForm):
    title = StringField('Movie Title', validators=[DataRequired()])
    submit = SubmitField('Add Movie')


@app.route('/')
def home():
    all_movies = db.session.query(Movie).order_by(Movie.rating.desc()).all()
    for movie in all_movies:
        movie.ranking = all_movies.index(movie) + 1
    db.session.commit()
    return render_template('index.html', movies=all_movies)


@app.route('/add-movie', methods=['GET', 'POST'])
def add():
    form = AddMovie()
    if form.validate_on_submit():
        title = form.title.data
        response = requests.get(url=f'{API_URL}/search/movie', params={'api_key': API_KEY, 'query': title})
        movies_list = response.json()['results']
        return render_template('select.html', movies=movies_list)
    return render_template('add.html', form=form)


@app.route('/find')
def find_movie():
    movie_id = int(request.args.get('movie_id'))
    try:
        movie_id_db = Movie.query.filter_by(movie_id=movie_id).first().movie_id
    except AttributeError:
        movie_id_db = ''

    if movie_id != movie_id_db:
        response = requests.get(url=f'{API_URL}/movie/{movie_id}', params={'api_key': API_KEY})
        movie_details = response.json()
        new_movie = Movie(
            movie_id=movie_id,
            title=movie_details['title'],
            year=movie_details['release_date'].split('-')[0],
            description=movie_details['overview'],
            img_url=f"https://image.tmdb.org/t/p/w500{movie_details['poster_path']}"
        )
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for('edit', movie_id=new_movie.id))
    else:
        flash('The title is already on the list!', 'error')
        return redirect(url_for('add'))


@app.route('/edit', methods=['GET', 'POST'])
def edit():
    class RateMovieForm(FlaskForm):
        movie_rating = request.args.get('movie_rating')
        movie_review = request.args.get('movie_review')
        rating = FloatField('Your Rating Out of 10 e.g. 7.5', validators=[DataRequired(), NumberRange(min=0, max=10)], render_kw={'placeholder': movie_rating})
        review = StringField('Your Review', validators=[DataRequired()], render_kw={'placeholder': movie_review})
        submit = SubmitField('Done')

    form = RateMovieForm()
    movie_id = request.args.get('movie_id')
    movie_to_update = Movie.query.get(movie_id)
    if form.validate_on_submit():
        movie_to_update.rating = float(form.rating.data)
        movie_to_update.review = form.review.data.strip()
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('edit.html', movie=movie_to_update, form=form)


@app.route('/delete')
def delete():
    movie_id = request.args.get('movie_id')
    movie_to_delete = Movie.query.get(movie_id)
    db.session.delete(movie_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
