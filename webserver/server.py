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
        cmd = """ SELECT name FROM tagsmade where pid = :pid """
        cursor_inner = g.conn.execute(text(cmd), pid=result[0])

        my_tags = []
        for result_inner in cursor_inner:
            my_tags.append(result_inner[0])

        cursor_inner.close()
        posts.append({
            'pid': result[0],
            'tag': result[2],
            'title': result[3],
            'date': result[4].strftime('%B %d, %Y'),
            'caption': result[5],
            'photo': result[6],
            'tags': my_tags
            })
    cursor.close()


    # Get all categories

    cursor = g.conn.execute('SELECT * FROM category')
    categories = []
    for result in cursor:
        categories.append({
            'name': result[0]
            })
    cursor.close()

    context = {'tags': tags, 'posts': posts, 'categories': categories}
    return render_template('index.html', **context)


#make post
@app.route('/posts/makepost')
def make_post():

    # Get all tags
    cursor = g.conn.execute('SELECT * FROM tags')

    tags = []
    for result in cursor:
        tags.append(result[0])
    cursor.close()

    # Get last record
    cursor = g.conn.execute('SELECT MAX(pid) FROM post')

    pid = 0
    for result in cursor:
        pid = result[0]
    cursor.close()


    cursor = g.conn.execute('SELECT * FROM category')
    categories = []
    for result in cursor:
        categories.append({
            'name': result[0]
            })
    cursor.close()

    context = {'tags': tags, 'pid': pid, 'categories': categories}
    return render_template('make_post.html', **context)


#save post
@app.route('/posts/savepost', methods=['POST'])
def save_post():
    title = str(request.form['title'])
    category = str(request.form['category'])
    description= str(request.form['description'])
    tag = str(request.form['tag'])
    pid = int(request.form['pid']) + 1

    tagList = tag.split(', ')

    cmd = \
         """ SELECT COUNT(*) FROM category
                WHERE name = :name """
    cursor = g.conn.execute(text(cmd), name=category )

    for result in cursor:
        if result[0] == 0:
            cmd = \
            """ INSERT INTO category(name, description, uid)
                VALUES(:name, :description, :uid) """
            g.conn.execute(text(cmd),name=category, description='This is a {} cateory'.format(category), uid=1)
    cursor.close()

    cmd = \
        """ INSERT INTO post(pid, uid, c_name, title, upload_date, description, upvotes, downvotes)
            VALUES(:pid, :uid, :c_name, :title, :upload_date, :description, :upvotes, :downvotes) """
    g.conn.execute(text(cmd),pid=pid, uid=1, c_name=category, title=title, upload_date=datetime.now(), description=description, upvotes=0, downvotes=0)

    for my_tag in tagList:
        cmd = """ INSERT INTO tagsmade(name, pid) VALUES(:name, :pid) """
        g.conn.execute(text(cmd),name=my_tag, pid=pid)

    return redirect('/posts/today')


# hall of fame
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
        cmd = """ SELECT name FROM tagsmade where pid = :pid """
        cursor_inner = g.conn.execute(text(cmd), pid=result[0])

        my_tags = []
        for result_inner in cursor_inner:
            my_tags.append(result_inner[0])

        cursor_inner.close()
        posts.append({
            'pid': result[0],
            'tag': result[2],
            'title': result[3],
            'date': result[4].strftime('%B %d, %Y'),
            'caption': result[5],
            'photo': result[6],
            'tags': my_tags
            })

        # Get all categories

    cursor = g.conn.execute('SELECT * FROM category')

    categories = []
    for result in cursor:
        categories.append({
            'name': result[0]
            })
    cursor.close()

    context = {'tags': tags, 'posts': posts, 'categories': categories}
    return render_template('hall_of_fame.html', **context)


# post page
@app.route('/post/<pid>')
def post(pid):
    # Get all tags

    cursor = g.conn.execute('SELECT * FROM tags')

    tags = []
    for result in cursor:
        tags.append(result[0])
    cursor.close()

    # Get all categories

    cursor = g.conn.execute('SELECT * FROM category')

    categories = []
    for result in cursor:
        categories.append({
            'name': result[0]
            })

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

        cmd = """ SELECT name FROM tagsmade where pid = :pid """
        cursor_inner = g.conn.execute(text(cmd), pid=result[0])

        my_tags = []
        for result_inner in cursor_inner:
            my_tags.append(result_inner[0])

        cursor_inner.close()

        post = {
                'pid': result[0],
                'uid': result[1],
                'tag': result[2],
                'title': result[3],
                'date': result[4].strftime('%B %d, %Y'),
                'caption': result[5],
                'photo': result[6],
                'like': result[7],
                'dislike': result[8],
                'tags': my_tags
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
                SELECT U.email, U.uid FROM users AS U
                    WHERE U.uid=:uid
                    LIMIT 1
            """
        temp_cursor = g.conn.execute(text(cmd), uid=uid)
        temp_result = temp_cursor.fetchone()

        username = temp_result[0].split('@')[0]
        comments.append({
            'content': result[0],
            'time': result[1].strftime('%b %d %y, %-I%p'),
            'username': username,
            'uid': temp_result[1]
        })

        temp_cursor.close()
    cursor.close()

    context = {'tags': tags, 'post': post, 'categories': categories, 'comments': comments, 'username': username}
    return render_template('post.html', **context)


# today's post
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
        cmd = """ SELECT name FROM tagsmade where pid = :pid """
        cursor_inner = g.conn.execute(text(cmd), pid=result[0])

        my_tags = []
        for result_inner in cursor_inner:
            my_tags.append(result_inner[0])

        cursor_inner.close()
        posts.append({
            'pid': result[0],
            'tag': result[2],
            'title': result[3],
            'date': result[4].strftime('%B %d, %Y'),
            'caption': result[5],
            'photo': result[6],
            'tags': my_tags
            })

        # Get all categories

    cursor = g.conn.execute('SELECT * FROM category')

    categories = []
    for result in cursor:
        categories.append({
            'name': result[0]
            })

    cursor.close()

    context = {'tags': tags, 'posts': posts, 'categories':categories}
    return render_template('today.html', **context)


# tags page
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
        cmd = """ SELECT name FROM tagsmade where pid = :pid """
        cursor_inner = g.conn.execute(text(cmd), pid=result[0])

        my_tags = []
        for result_inner in cursor_inner:
            my_tags.append(result_inner[0])

        cursor_inner.close()
        posts.append({
            'pid': result[0],
            'tag': result[2],
            'title': result[3],
            'date': result[4].strftime('%B %d, %Y'),
            'caption': result[5],
            'photo': result[6],
            'tags': my_tags
            })
    cursor.close()

    cursor = g.conn.execute('SELECT * FROM category')
    categories = []
    for result in cursor:
        categories.append({
            'name': result[0]
            })
    cursor.close()

    context = {'tags': tags, 'posts': posts, 'tag': tag, 'categories': categories}
    return render_template('posts_with_tag.html', **context)


# category page
@app.route('/posts/category/<category>')
def posts_with_category(category):

    # Get all tagg
    cursor = g.conn.execute('SELECT * FROM tags')

    tags = []
    for result in cursor:
        tags.append(result[0])


    # Get all posts with tag

    cmd = \
        """
            SELECT * FROM post AS P
                WHERE c_name=:category

        """
    cursor = g.conn.execute(text(cmd), category=category)

    posts = []
    for result in cursor:

        cmd = """ SELECT name FROM tagsmade where pid = :pid """
        cursor_inner = g.conn.execute(text(cmd), pid=result[0])

        my_tags = []
        for result_inner in cursor_inner:
            my_tags.append(result_inner[0])

        cursor_inner.close()

        posts.append({
            'pid': result[0],
            'tag': result[2],
            'title': result[3],
            'date': result[4].strftime('%B %d, %Y'),
            'caption': result[5],
            'photo': result[6],
            'tags': my_tags
            })

    cursor = g.conn.execute('SELECT * FROM category')

    categories = []
    for result in cursor:
        categories.append({
            'name': result[0]
            })

    cursor.close()

    context = {'tags': tags, 'posts': posts, 'categories': categories, 'category': category}
    return render_template('posts_with_cat.html', **context)


#trending page
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
        cmd = """ SELECT name FROM tagsmade where pid = :pid """
        cursor_inner = g.conn.execute(text(cmd), pid=result[0])

        my_tags = []
        for result_inner in cursor_inner:
            my_tags.append(result_inner[0])

        cursor_inner.close()

        posts.append({
            'pid': result[0],
            'tag': result[2],
            'title': result[3],
            'date': result[4].strftime('%B %d, %Y'),
            'caption': result[5],
            'photo': result[6],
            'tags': my_tags
            })
    cursor.close()
        # Get all categories

    cursor = g.conn.execute('SELECT * FROM category')

    categories = []
    for result in cursor:
        categories.append({
            'name': result[0]
            })

    cursor.close()

    context = {'tags': tags, 'posts': posts, 'categories': categories}
    return render_template('trending.html', **context)



@app.route('/subscribe/<sid>/<uid>')
def subscribe(sid, uid):

    # Subscribe user 1 (uid) to user 2 (sid)
    if sid != uid:
        cmd = \
            """
                INSERT INTO subscribe(sid, uid)
                    VALUES (:sid, :uid)
                ON CONFLICT DO NOTHING
            """
        g.conn.execute(text(cmd), sid=sid, uid=uid)

    return redirect('/profile/%s' % uid)


@app.route('/profile/<uid>')
def profile(uid):

    # Get all tags

    cursor = g.conn.execute('SELECT * FROM tags')
    tags = []
    for result in cursor:
        tags.append(result[0])
    cursor.close()

    # Get info about current user

    cmd = \
        """
            SELECT * FROM users AS U
                WHERE U.uid=:uid
            LIMIT 1
        """
    cursor = g.conn.execute(text(cmd), uid=uid)
    result = cursor.fetchone()
    account = {
        'uid': result[0],
        'name': "%s %s" % (result[1], result[2]),
        'birthdate': result[3].strftime('%B %d, %Y'),
        'email': result[4],
        'username': (result[4].split('@'))[0],
        'bio': result[7]
    }
    cursor.close()

    # Get all subscribers for a user

    cmd = \
        """
            SELECT S.uid FROM subscribe AS S
                WHERE S.sid=:uid
         """

    cursor = g.conn.execute(text(cmd), uid=uid)
    sids = []
    for result in cursor:
        sids.append(result[0])
    cursor.close()

    # Get data about each subscriber

    subscribers = []
    for sid in sids:
        cmd = \
            """
                SELECT U.uid, U.fname, U.lname , U.email FROM users AS U
                    WHERE U.uid=:uid
            """
        cursor = g.conn.execute(text(cmd), uid=sid)
        for result in cursor:
            subscribers.append({
                'uid': result[0],
                'name': "%s %s" % (result[1], result[2]),
                'username': (result[3].split('@'))[0]
            })
        cursor.close()

    context = { 'tags': tags, 'subscribers': subscribers, 'account': account }
    return render_template('profile.html', **context)

#comment
@app.route('/comment/<pid>', methods=['POST'])
def add_comment(pid):

    # Add comment to post
    content = str(request.form['content'])


    cmd = """ INSERT INTO comment(content, time, uid, pid) VALUES(:content, :time, :uid, :pid) """
    g.conn.execute(text(cmd),content=content, time=datetime.now(), uid=1, pid=pid)

    return redirect('/post/%s'%pid)


#like
@app.route('/like/<pid>')
def like_post(pid):

    cmd = \
         """ SELECT COUNT(*) FROM vote
                WHERE pid = :pid AND uid =:uid """
    cursor = g.conn.execute(text(cmd), pid=pid, uid=1)

    for result in cursor:
        if result[0] == 0:
            cmd = """ INSERT INTO vote(pid, uid, vote_type) VALUES(:pid, :uid, :vote) """
            g.conn.execute(text(cmd),pid=pid, uid=1, vote=True)

            cmd = """ SELECT upvotes FROM post WHERE pid = :pid """
            cursor_inner = g.conn.execute(text(cmd), pid=pid)

            ilike = 0
            for result_inner in cursor_inner:
                ilike = result_inner[0] + 1
            cursor_inner.close()

            cmd = """ UPDATE post SET upvotes = :ilike WHERE pid = :pid """
            g.conn.execute(text(cmd), ilike=ilike, pid=pid)
        else:
            cmd = \
                """ SELECT vote_type FROM vote
                    WHERE pid = :pid AND uid =:uid """
            cursor_inner = g.conn.execute(text(cmd), pid=pid, uid=1)

            for result_inner in cursor_inner:
                if result_inner[0] == False:
                    cmd = """ UPDATE vote SET vote_type = True WHERE pid = :pid AND uid = :uid """
                    g.conn.execute(text(cmd),pid=pid, uid=1)

                cmd = """ SELECT upvotes, downvotes FROM post WHERE pid = :pid """
                cursor_inner_two = g.conn.execute(text(cmd), pid=pid)

                ilike = 0
                dislike = 0
                for result_inner_two in cursor_inner_two:
                    ilike = result_inner_two[0] + 1
                    dislike = result_inner_two[1] - 1
                cursor_inner_two.close()

                cmd = """ UPDATE post SET upvotes = :ilike, downvotes = :dislike WHERE pid = :pid """
                g.conn.execute(text(cmd), ilike=ilike, dislike=dislike, pid=pid)
            cursor_inner.close()
    cursor.close()

    return redirect('/post/%s'%pid)

# dislike
@app.route('/dislike/<pid>')
def dislike_post(pid):

    cmd = \
         """ SELECT COUNT(*) FROM vote
                WHERE pid = :pid AND uid =:uid """
    cursor = g.conn.execute(text(cmd), pid=pid, uid=1)

    for result in cursor:
        if result[0] == 0:
            cmd = """ INSERT INTO vote(pid, uid, vote_type) VALUES(:pid, :uid, :vote) """
            g.conn.execute(text(cmd),pid=pid, uid=1, vote=False)

            cmd = """ SELECT downvotes FROM post WHERE pid = :pid """
            cursor_inner = g.conn.execute(text(cmd), pid=pid)

            dislike = 0
            for result_inner in cursor_inner:
                dislike = result_inner[0] + 1
            cursor_inner.close()

            cmd = """ UPDATE post SET downvotes = :dislike WHERE pid = :pid """
            g.conn.execute(text(cmd), dislike=dislike, pid=pid)
        else:
            cmd = \
                """ SELECT vote_type FROM vote
                    WHERE pid = :pid AND uid =:uid """
            cursor_inner = g.conn.execute(text(cmd), pid=pid, uid=1)

            for result_inner in cursor_inner:
                if result_inner[0] == False:
                    cmd = """ UPDATE vote SET vote_type = False WHERE pid = :pid AND uid = :uid """
                    g.conn.execute(text(cmd),pid=pid, uid=1)

                cmd = """ SELECT upvotes, downvotes FROM post WHERE pid = :pid """
                cursor_inner_two = g.conn.execute(text(cmd), pid=pid)

                ilike = 0
                dislike = 0
                for result_inner_two in cursor_inner_two:
                    ilike = result_inner_two[0] - 1
                    dislike = result_inner_two[1] + 1
                cursor_inner_two.close()

                cmd = """ UPDATE post SET upvotes = :ilike, downvotes = :dislike WHERE pid = :pid """
                g.conn.execute(text(cmd), ilike=ilike, dislike=dislike, pid=pid)
            cursor_inner.close()
    cursor.close()

    return redirect('/post/%s'%pid)


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
