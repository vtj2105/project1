#!/usr/bin/env python2.7

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response
from datetime import datetime

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'templates')
app = Flask(__name__, template_folder=tmpl_dir)

DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_SERVER = 'w4111.cisxo09blonu.us-east-1.rds.amazonaws.com'
DATABASEURI = 'postgresql://' + DB_USER + ':' + DB_PASSWORD + '@' \
    + DB_SERVER + '/w4111'

engine = create_engine(DATABASEURI, echo=True)


@app.before_request
def before_request():
    try:
        g.conn = engine.connect()
    except:
        print('problem connecting to database')
        import traceback
        traceback.print_exc()
        g.conn = None


@app.teardown_request
def teardown_request(exception):
    try:
        g.conn.close()
    except Exception as e:
        pass


@app.route('/')
def index():

  # Get all tags

    cursor = g.conn.execute('SELECT * FROM tags')

    tags = []
    for result in cursor:
        tags.append(result[0])
    cursor.close()

  # Get all posts

    cursor = g.conn.execute('SELECT * FROM post')

    posts = []
    for result in cursor:
        posts.append({
            'pid': result[0],
            'tag': result[2],
            'title': result[3],
            'date': result[4].strftime('%B %d, %Y'),
            'caption': result[5],
            'photo': result[6],
            })
    cursor.close()

    context = {'tags': tags, 'posts': posts}
    return render_template('index.html', **context)


@app.route('/posts/hall_of_fame')
def hall_of_fame():

    # Get all tags

    cursor = g.conn.execute('SELECT * FROM tags')

    tags = []
    for result in cursor:
        tags.append(result[0])
    cursor.close()

    # Get the top ten posts with the most likes

    cmd = \
        """
            SELECT * FROM post AS P
                WHERE P.upvotes > 0
                ORDER BY P.upvotes DESC
                LIMIT 10;
        """
    cursor = g.conn.execute(text(cmd))

    posts = []
    for result in cursor:
        posts.append({
            'pid': result[0],
            'tag': result[2],
            'title': result[3],
            'date': result[4].strftime('%B %d, %Y'),
            'caption': result[5],
            'photo': result[6],
            })
    cursor.close()

    context = {'tags': tags, 'posts': posts}
    return render_template('hall_of_fame.html', **context)

@app.route('/post/<pid>')
def post(pid):
    # Get all tags

    cursor = g.conn.execute('SELECT * FROM tags')

    tags = []
    for result in cursor:
        tags.append(result[0])
    cursor.close()

    # Get post by pid

    cmd = \
        """
            SELECT * FROM post AS P
                WHERE P.pid=:pid
                LIMIT 1
        """
    cursor = g.conn.execute(text(cmd), pid=pid)
    if cursor.rowcount == 0:
        context = {'post': None, 'tags': tags}
        return render_template('post.html', **context)

    result = cursor.fetchone()
    post = {}
    if result:
        post = {
                'pid': result[0],
                'uid': result[1],
                'tag': result[2],
                'title': result[3],
                'date': result[4].strftime('%B %d, %Y'),
                'caption': result[5],
                'photo': result[6],
        }
    cursor.close()

    # Get creator of post

    cmd = \
        """
            SELECT fname, lname FROM users AS U
                WHERE U.uid=:uid
                LIMIT 1
        """
    cursor = g.conn.execute(text(cmd), uid=post['uid'])
    result = cursor.fetchone()
    username = "%s %s" % (result[0], result[1])

    # Get post comments

    cmd = \
        """
            SELECT content, time, uid FROM comment AS C
                WHERE C.pid=:pid
        """
    cursor = g.conn.execute(text(cmd), pid=pid)
    comments = []

    for result in cursor:
        # Get username for comment creator

        uid = result[2]

        cmd = \
            """
                SELECT email FROM users AS U
                    WHERE U.uid=:uid
                    LIMIT 1
            """
        temp_cursor = g.conn.execute(text(cmd), uid=uid)
        temp_result = temp_cursor.fetchone()

        username = temp_result[0].split('@')[0]
        comments.append({
            'content': result[0],
            'time': result[1].strftime('%B %d, %Y'),
            'username': username
        })

        temp_cursor.close()
    cursor.close()

    context = {'tags': tags, 'post': post, 'comments': comments, 'username': username}
    return render_template('post.html', **context)

@app.route('/posts/today')
def posts_today():

    # Get all tags

    cursor = g.conn.execute('SELECT * FROM tags')

    tags = []
    for result in cursor:
        tags.append(result[0])
    cursor.close()

    # Get posts uploaded today

    cmd = \
        """
            SELECT * FROM post AS P
                WHERE P.upload_date=CURRENT_DATE
        """
    cursor = g.conn.execute(text(cmd))

    posts = []
    for result in cursor:
        posts.append({
            'pid': result[0],
            'tag': result[2],
            'title': result[3],
            'date': result[4].strftime('%B %d, %Y'),
            'caption': result[5],
            'photo': result[6],
            })
    cursor.close()

    context = {'tags': tags, 'posts': posts}
    return render_template('today.html', **context)


@app.route('/posts/tag/<tag>')
def posts_with_tag(tag):

    # Get all tags

    cursor = g.conn.execute('SELECT * FROM tags')

    tags = []
    for result in cursor:
        tags.append(result[0])
    cursor.close()

    # Get all posts with tag

    cmd = \
        """
            SELECT * FROM post AS P
                WHERE P.pid IN (
                    SELECT T.pid FROM tagsmade AS T
                        WHERE T.name=:tag
                )
        """
    cursor = g.conn.execute(text(cmd), tag=tag)

    posts = []
    for result in cursor:
        posts.append({
            'pid': result[0],
            'tag': result[2],
            'title': result[3],
            'date': result[4].strftime('%B %d, %Y'),
            'caption': result[5],
            'photo': result[6],
            })
    cursor.close()

    context = {'tags': tags, 'posts': posts, 'tag': tag}
    return render_template('posts_with_tag.html', **context)

@app.route('/comment/<content>/<pid>')
def add_comment(content, pid):

    # Add comment to post

    cmd = """INSERT INTO comment(content, time, uid, pid) VALUES (:content, :time, :uid, :pid);"""
    engine.execute(text(cmd), content=content, time=datetime.now(), uid=1, pid=pid)

    return redirect('/post/%s' % pid)


@app.route('/posts/trending')
def posts_trending():

    # Get all tags

    cursor = g.conn.execute('SELECT * FROM tags')
    tags = []
    for result in cursor:
        tags.append(result[0])
    cursor.close()

    # Get all posts trending this week

    cmd = \
        """
          SELECT * FROM post AS P
              WHERE P.upvotes > 0 AND
                P.upload_date > CURRENT_DATE - integer '7' AND
                P.upload_date <= CURRENT_DATE
              ORDER BY P.upvotes DESC
              LIMIT 10;
        """
    cursor = g.conn.execute(text(cmd))

    posts = []
    for result in cursor:
        posts.append({
            'pid': result[0],
            'tag': result[2],
            'title': result[3],
            'date': result[4].strftime('%B %d, %Y'),
            'caption': result[5],
            'photo': result[6],
            })
    cursor.close()

    context = {'tags': tags, 'posts': posts}
    return render_template('trending.html', **context)

if __name__ == '__main__':
    import click


    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    def run(
        debug,
        threaded,
        host,
        port,
        ):
        (HOST, PORT) = (host, port)
        print('running on %s:%d' % (HOST, PORT))
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

    run()
