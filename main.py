from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length
import requests
import os


search_movie_url = "https://api.themoviedb.org/3/search/movie?query={title}&include_adult=false&language=en-US&page=1"
get_movie_url = "https://api.themoviedb.org/3/movie/{id}?language=en-US"
movies_image_url = "https://image.tmdb.org/t/p/w500"
bearer_token = f"Bearer {os.environ.get('TOKEN')}"

headers = {
    "accept": "application/json",
    "Authorization": bearer_token
}

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap5(app)


class EditForm(FlaskForm):
    rating = StringField('Your rating out of 10', validators=[DataRequired()])
    review = StringField('Your review', validators=[DataRequired(), Length(min=1, max=75)])
    submit = SubmitField('Done')


class AddForm(FlaskForm):
    title = StringField('Movie title', validators=[DataRequired()])
    submit = SubmitField('Add movie')


def SearchMoviesByTitle(title):
    response = requests.get(search_movie_url.format(title=title), headers=headers)
    response.raise_for_status()
    return response.json()['results']


def GetMovieById(movie_id):
    response = requests.get(get_movie_url.format(id=movie_id), headers=headers)
    response.raise_for_status()
    return response.json()


# CREATE DB
class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# configure the SQLite database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///top-movies.db"
# initialize the app with the extension
db.init_app(app)


# CREATE TABLE
class Movie(db.Model):
    id: Mapped[id] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    ranking: Mapped[int] = mapped_column(Integer, nullable=False)
    review: Mapped[str] = mapped_column(String(250), nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)


with app.app_context():
    db.create_all()


@app.route("/")
def home():
    result = db.session.execute(db.select(Movie).order_by(Movie.rating))
    all_movies = result.scalars().all()

    # Recalculate the ranking according to the rating
    for i in range(len(all_movies)):
        all_movies[i].ranking = len(all_movies) - i
    db.session.commit()

    return render_template("index.html", movies=all_movies)


@app.route("/edit", methods=['GET', 'POST'])
def edit():
    form = EditForm()
    movie = db.get_or_404(Movie, request.args.get('movie_id'))

    if form.validate_on_submit():
        movie.rating = float(form.rating.data)
        movie.review = form.review.data
        db.session.commit()
        return redirect(url_for('home'))

    return render_template("edit.html", form=form, movie=movie)


@app.route("/delete")
def delete():
    movie = db.get_or_404(Movie, request.args.get('movie_id'))
    db.session.delete(movie)
    db.session.commit()
    return redirect(url_for('home'))


@app.route("/add", methods=['GET', 'POST'])
def add():
    form = AddForm()

    if form.validate_on_submit():
        movies = SearchMoviesByTitle(form.title.data)
        return render_template("select.html", movies=movies)

    return render_template("add.html", form=form)


@app.route("/find")
def find():
    movie_json = GetMovieById(request.args.get('movie_id'))
    new_movie = Movie(title=movie_json["title"],
                      year=movie_json["release_date"].split("-")[0],
                      img_url=f"{movies_image_url}{movie_json['poster_path']}",
                      description=movie_json["overview"],
                      rating=0,
                      review="",
                      ranking=0)
    db.session.add(new_movie)
    db.session.commit()

    return redirect(url_for("edit", movie_id=new_movie.id))


if __name__ == '__main__':
    app.run(debug=True)
