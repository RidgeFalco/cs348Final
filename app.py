# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
import functools
from flask import Flask, request, redirect, render_template, session, url_for, flash, g
from werkzeug.security import check_password_hash, generate_password_hash

# Import SQLAlchemy, this will be the main way I interact with my Postgres database
from sqlalchemy import create_engine, ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.sql import func
from typing import Optional

# Creating ORM mapped classes for tables
class Base(DeclarativeBase):
    pass

# Table for user accounts
class User(Base):
    __tablename__ = "user_account"
    
    user_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    password: Mapped[str]
    add_music_perm: Mapped[Optional[bool]]

# Table for artists
class Artist(Base):
    __tablename__ = "artists"

    artist_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

# Table for albums, have a foreign key to the artist who made the album
class Album(Base):
    __tablename__ = "albums"

    album_id: Mapped[int] = mapped_column(primary_key=True)
    album_name: Mapped[str]
    num_of_songs: Mapped[int]
    artist = mapped_column(ForeignKey("artists.artist_id"))

class AlbumReview(Base):
    __tablename__ = "albumreviews"

    review_id: Mapped[int] = mapped_column(primary_key=True)
    score: Mapped[float] = mapped_column(index=True)
    text: Mapped[str]
    album = mapped_column(ForeignKey("albums.album_id"), index=True)
    user = mapped_column(ForeignKey("user_account.user_id"))


# Creating the connection to the Postgresql database
engine = create_engine("postgresql+psycopg2://rfalco:POSTthis!!!@localhost:5432/cs348", echo=True)

# Setting up a read uncommitted option for the engine
uncommitted_engine = engine.execution_options(isolation_level="READ UNCOMMITTED")

# Create session maker factory
Session = sessionmaker(engine)

# Create all the tables that are defined above
Base.metadata.create_all(engine)

# Flask constructor takes the name of 
# current module (__name__) as argument.
app = Flask(__name__)

# Need secret key, just set as dev for now
app.config.from_mapping(SECRET_KEY='dev')
app.add_url_rule('/', endpoint='index')

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('login'))

        return view(**kwargs)

    return wrapped_view

# The route() function of the Flask class is a decorator, 
# which tells the application which URL should call 
# the associated function.
@app.route('/')
# ‘/’ URL is bound with hello_world() function.
@login_required
def index():
    with Session() as sesh:
        result = sesh.scalars(select(User))
        # print(result)
        return render_template('index.html', content=result)

@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        sec_pass = generate_password_hash(password)

        error = None

        if not username and not password:
            error = 'Username and password is required.'
        elif not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'

        if error is None:
            with Session() as sesh:
                result = sesh.query(User).count()

                if result == 0:
                    new_user = User(username=username, password=sec_pass, add_music_perm=True)
                else:
                    new_user = User(username=username, password=sec_pass, add_music_perm=False)
                sesh.add(new_user)
                
                try:
                    sesh.commit()
                except:
                    error = 'User with that username already exists!'

            if error is None:
                return redirect(url_for("login"))
            else:
                flash(error)
                return redirect(url_for("register"))
            

        flash(error)

    return render_template('register.html')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        error = None

        with Session() as sesh:
            result = sesh.scalar(select(User).where(User.username == username))

            # print(result)

            if result is None:
                error = 'Incorrect username!'
            elif not check_password_hash(result.password, password):
                error = 'Incorrect password!!!'

            if error is None:
                session.clear()
                session['user_id'] = result.user_id
                return redirect(url_for('index'))

        flash(error)
    
    return render_template('login.html')

@app.route('/passwordchange', methods=('GET', 'POST'))
@login_required
def change_pass():
    if request.method == 'POST':
        newpassword = request.form['newpassword']
        error = None

        if not newpassword:
            error = 'New password is required.'
        
        if error is not None:
            flash(error)
        else:
            with Session() as sesh:
                result = sesh.scalar(select(User).where(User.user_id == g.user.user_id))
                result.password = generate_password_hash(newpassword)
                sesh.commit()
                return redirect(url_for('index'))
    
    return render_template('change.html')


@app.route('/deleteuser', methods=('GET', 'POST'))
@login_required
def delete_user():
    if request.method == 'POST':
        with Session() as sesh:
            result = sesh.scalar(select(User).where(User.user_id == g.user.user_id))
            sesh.delete(result)
            sesh.commit()
            return redirect(url_for('index'))

    return render_template('delete.html')

@app.route('/addalbum', methods=('GET', 'POST'))
@login_required
def add_album():
    if request.method == 'POST':
        albumName = request.form['album_title']
        numOfTracks = request.form['song_count']
        artistName = request.form['artist']
        error = None

        if not albumName or not numOfTracks or not artistName:
            error = 'Please enter info for all three fields'
        
        if error is not None:
            flash(error)
        else:
            with Session() as sesh:
                artistResult = sesh.scalar(select(Artist).where(Artist.name == artistName))

                if artistResult is None:
                    newArtist = Artist(name=artistName)
                    sesh.add(newArtist)
                    artistResult = sesh.scalar(select(Artist).where(Artist.name == artistName))

                artistId = artistResult.artist_id

                newAlbum = Album(album_name=albumName, num_of_songs = numOfTracks, artist = artistId)
                sesh.add(newAlbum)
                sesh.commit()

                return redirect(url_for('index'))
    
    return render_template('addalbum.html')

@app.route('/addreview', methods=('GET', 'POST'))
@login_required
def add_review():
    if request.method == 'POST':
        albumName = request.form['album_name']
        rating = request.form['rating']
        text = request.form['text']
        error = None

        if not albumName or not rating or not text:
            error = 'Please enter info for all three fields'
        
        if error is not None:
            flash(error)
        else:
            with Session() as sesh:
                # print(albumName)
                # print(rating)
                # print(text)
                albumId = sesh.scalar(select(Album).where(Album.album_name == albumName)).album_id

                newReview = AlbumReview(score=rating, text = text, album = albumId, user = session.get('user_id'))
                sesh.add(newReview)
                sesh.commit()

                return redirect(url_for('index'))
    
    with Session() as sesh:
        result = sesh.scalars(select(Album))
        return render_template('addreview.html', content=result)

@app.route('/albums', methods=('GET', 'POST'))
def show_albums():
    if request.method == 'POST':
        albumName = request.form['album_name']
        error = None

        if not albumName:
            error = 'Please select an album!'

        if error is not None:
            flash(error)
        else:
            with Session(bind=uncommitted_engine) as sesh:
                albumId = sesh.scalar(select(Album).where(Album.album_name == albumName)).album_id

                avgRatingStmt = select(func.avg(AlbumReview.score).label("AverageRating")).where(AlbumReview.album == albumId)

                avgRating = sesh.execute(avgRatingStmt).first()
                # print(f"{avgRating.AverageRating}")

                reviewsStmt = select(AlbumReview.score.label("rating"), AlbumReview.text.label("text"), User.username.label("username")).join(User).where(AlbumReview.album == albumId)

                content = sesh.execute(reviewsStmt)

                return render_template('reviews.html', avgRating=avgRating.AverageRating, albumName=albumName, content=content)

    with Session() as sesh:
        result = sesh.scalars(select(Album))
        return render_template('albums.html', content=result)

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')

    # print(user_id)

    if user_id is None:
        g.user = None
    else:
        with Session() as sesh:
            g.user = sesh.scalar(select(User).where(User.user_id == user_id))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# main driver function
if __name__ == '__main__':
    # run() method of Flask class runs the application 
    # on the local development server.
    app.run()
