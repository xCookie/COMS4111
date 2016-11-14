# all the imports
import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://qx2155:cj9sw@104.196.175.120/postgres",
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])

@app.before_request
def before_request():
    try:
        g.conn = engine.connect()
    except:
        print "uh oh, problem connecting to database"
        import traceback; traceback.print_exc()
        g.conn = None

@app.teardown_request
def teardown_request(exception):
    try:
        g.conn.close()
    except Exception as e:
        pass

#### Index
@app.route('/')
def index():
    return render_template('index.html')

#### Clients side
@app.route('/clients/add/', methods=['POST'])
def clients_add():
    error = None
    db = g.conn
    try:
        db.execute('insert into users(uid, name, email) values (%s, %s, %s)',
                     [request.form['uid'], request.form['name'], request.form['email']])
        if request.form['date'] != '':
            db.execute('insert into clients(uid, dateofbirth) values (%s, %s)',
            [request.form['uid'], request.form['date']])
        else:
            db.execute('insert into clients(uid) values (%s)',
            request.form['uid'])
        flash('Registration is successful!')
    except AttributeError:
        error = 'FATAL:  remaining connection slots are reserved for non-replication superuser connections'
    except Exception as e:
        error = e
    return render_template('index.html', error=error)

@app.route('/clients/<uid>/')
def clients(uid=None):
    if not session.get('logged_in_uid') == uid:
        abort(401)

    db = g.conn
    error = None
    orders = []
    has_dish = []
    info = {}
    try:
        orders = db.execute('select * from orders_places as o, users as m where o.uid=(%s) and o.mid=m.uid order by o.ord_time DESC', uid).fetchall()
        has_dish = db.execute('select * from (select * from has as h, dishes as d where h.did=d.did) as hd, (select * from orders_places where uid=(%s)) as ord where hd.ord_id=ord.ord_id', uid).fetchall()
        info = db.execute('select * from clients as c, users as u where c.uid=u.uid and c.uid=(%s)', uid).fetchone()
    except AttributeError:
        error = 'FATAL:  remaining connection slots are reserved for non-replication superuser connections'
    except Exception as e:
        error = e
    return render_template('clients.html', orders=orders, has_dish=has_dish, info=info, error=error)

@app.route('/clients/<uid>/update/', methods=['POST'])
def clients_update(uid=None):
    if not session.get('logged_in_uid') == uid:
        abort(401)

    db = g.conn
    error = None
    name = request.form['name']
    email = request.form['email']
    date = request.form['date']
    try:
        db.execute('update users set name=(%s), email=(%s) where uid=(%s)', [name, email, uid])
        db.execute('update clients set dateofbirth=(%s) where uid=(%s)', [date, uid])
        session['logged_in_name'] = name
        flash('Update successfully!')
    except AttributeError:
        error = 'FATAL:  remaining connection slots are reserved for non-replication superuser connections'
        flash(error)
    except Exception as e:
        error = e
        flash(error)
    return redirect(url_for('clients', uid=uid))

##### Orders side
@app.route('/orders/<mid>/add/', methods=['POST'])
def orders_add(mid=None):
    if not session.get('logged_in_as') == 'client':
        abort(401)

    db = g.conn
    tel_number = request.form['phone']
    address = request.form['address']
    status = '0'
    uid = session.get('logged_in_uid')
    try:
        db.execute('insert into orders_places(tel_number, address, status, uid, mid) values (%s, %s, %s, %s, %s)',
         [tel_number, address, status, uid, mid])
        flash('Order created!')
    except AttributeError:
        error = 'FATAL:  remaining connection slots are reserved for non-replication superuser connections'
        flash(error)
    except Exception as e:
        error = e
        flash(error)

    return redirect(url_for('merchants', uid=mid))

@app.route('/orders/<uid>/<ord_id>/cancel/')
def orders_cancel(uid=None, ord_id=None):
    if not session.get('logged_in_uid') == uid:
        abort(401)

    db = g.conn
    try:
        db.execute('update orders_places set status=(%s) where ord_id=(%s)', ['2', ord_id])
        flash('Order cancelled!')
    except AttributeError:
        error = 'FATAL:  remaining connection slots are reserved for non-replication superuser connections'
        flash(error)
    except Exception as e:
        error = e
        flash(error)

    return redirect(url_for('clients', uid=uid))

@app.route('/orders/<uid>/<ord_id>/complete/')
def orders_complete(uid=None, ord_id=None):
    if not session.get('logged_in_uid') == uid:
        abort(401)

    db = g.conn
    try:
        db.execute('update orders_places set status=(%s) where ord_id=(%s)', ['1', ord_id])
        flash('Order completed!')
    except AttributeError:
        error = 'FATAL:  remaining connection slots are reserved for non-replication superuser connections'
        flash(error)
    except Exception as e:
        error = e
        flash(error)

    return redirect(url_for('merchants_orders', uid=uid))

@app.route('/orders/<mid>/<did>/update/', methods=['POST'])
def orders_update(did=None, mid=None):
    if not session.get('logged_in_as') == 'client':
        abort(401)

    db = g.conn
    ord_number = request.form['number']
    ord_id = request.form['order']
    try:
        db.execute('insert into has(ord_number, did, ord_id) values (%s, %s, %s)',
         [ord_number, did, ord_id])
        flash('Dish added to selected order!')
    except AttributeError:
        error = 'FATAL:  remaining connection slots are reserved for non-replication superuser connections'
        flash(error)
    except Exception as e:
        error = e
        flash(error)

    return redirect(url_for('merchants', uid=mid))

##### Merchents side
@app.route('/merchants/<uid>/')
def merchants(uid=None):
    if not session.get('logged_in_as') == 'client':
        abort(401)

    error = None
    db = g.conn
    dishes = []
    orders = []
    reviews = []
    info = {}
    try:
        dishes = db.execute('select * from categories as c, (select * from merchants as m, dishes as d where m.uid=d.uid and m.uid=(%s)) as md where c.cid=md.cid', uid).fetchall()
        info = db.execute('select * from merchants as c, users as u where c.uid=u.uid and c.uid=(%s)', uid).fetchone()
        orders = db.execute('select * from orders_places where (uid=(%s) and status=(%s)) and mid=(%s)', [session.get('logged_in_uid'), '0', uid]).fetchall()
        reviews = db.execute('select * from (select * from reviews as r, users as u where r.uid=u.uid) as ru, dishes as d where ru.did=d.did and d.uid=(%s)', uid).fetchall()
    except AttributeError:
        error = 'FATAL:  remaining connection slots are reserved for non-replication superuser connections'
    except Exception as e:
        error = e
    return render_template('merchants.html', dishes=dishes, merchant=info, orders=orders, reviews=reviews, error=error)

@app.route('/merchants/<uid>/orders/')
def merchants_orders(uid=None):
    if not session.get('logged_in_uid') == uid:
        abort(401)

    db = g.conn
    error = None
    orders = []
    has_dish = []
    info = {}
    try:
        orders = db.execute('select * from orders_places as o, users as m where o.mid=(%s) and o.uid=m.uid order by o.ord_time DESC', uid).fetchall()
        has_dish = db.execute('select * from (select * from has as h, dishes as d where h.did=d.did) as hd, (select * from orders_places where mid=(%s)) as ord where hd.ord_id=ord.ord_id', uid).fetchall()
        info = db.execute('select * from merchants as c, users as u where c.uid=u.uid and c.uid=(%s)', uid).fetchone()
    except AttributeError:
        error = 'FATAL:  remaining connection slots are reserved for non-replication superuser connections'
    except Exception as e:
        error = e
    return render_template('merchants_orders.html', orders=orders, has_dish=has_dish, info=info, error=error)

@app.route('/merchants/<uid>/dishes/')
def merchants_dishes(uid=None):
    if not session.get('logged_in_uid') == uid:
        abort(401)

    error = None
    db = g.conn
    dishes = []
    reviews = []
    categories = []
    info = {}
    try:
        dishes = db.execute('select * from categories as c, (select * from merchants as m, dishes as d where m.uid=d.uid and m.uid=(%s)) as md where c.cid=md.cid', uid).fetchall()
        info = db.execute('select * from merchants as c, users as u where c.uid=u.uid and c.uid=(%s)', uid).fetchone()
        categories = db.execute('select * from categories').fetchall()
        reviews = db.execute('select * from (select * from reviews as r, users as u where r.uid=u.uid) as ru, dishes as d where ru.did=d.did and d.uid=(%s)', uid).fetchall()
    except AttributeError:
        error = 'FATAL:  remaining connection slots are reserved for non-replication superuser connections'
    except Exception as e:
        error = e
    return render_template('merchants_dishes.html', dishes=dishes, merchant=info, reviews=reviews, categories=categories, error=error)

@app.route('/merchants/<uid>/update/', methods=['POST'])
def merchants_update(uid=None):
    if not session.get('logged_in_uid') == uid:
        abort(401)

    db = g.conn
    error = None
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    address = request.form['address']
    img = request.form['img']
    try:
        db.execute('update users set name=(%s), email=(%s) where uid=(%s)', [name, email, uid])
        db.execute('update merchants set tel_number=(%s), address=(%s), img=(%s) where uid=(%s)', [phone, address, img, uid])
        session['logged_in_name'] = name
        flash('Update successfully!')
    except AttributeError:
        error = 'FATAL:  remaining connection slots are reserved for non-replication superuser connections'
        flash(error)
    except Exception as e:
        error = e
        flash(error)
    return redirect(url_for('merchants_dishes', uid=uid))

@app.route('/merchants/all/')
def merchants_all():
    if not session.get('logged_in_as') == 'client':
        abort(401)

    error = None
    db = g.conn
    merchants = []
    try:
        merchants = db.execute('select * from merchants as m, users as u where m.uid=u.uid').fetchall()
    except AttributeError:
        error = 'FATAL:  remaining connection slots are reserved for non-replication superuser connections'
    except Exception as e:
        error = e
    return render_template('all_merchants.html', merchants=merchants)

@app.route('/merchants/add/', methods=['POST'])
def merchants_add():
    error = None
    db = g.conn
    try:
        db.execute('insert into users(uid, name, email) values (%s, %s, %s)',
                     [request.form['uid'], request.form['name'], request.form['email']])
        db.execute('insert into merchants(uid, address, tel_number, avg_rating, img) values (%s, %s, %s, %s, %s)',
            [request.form['uid'], request.form['address'], request.form['phone'], '5', request.form['img']])
        flash('Registration is successful!')
    except AttributeError:
        error = 'FATAL:  remaining connection slots are reserved for non-replication superuser connections'
    except Exception as e:
        error = e
    return render_template('index.html', error=error)

#### Dish side
@app.route('/dishes/<mid>/add/', methods=['POST'])
def dishes_add(mid=None):
    if not session.get('logged_in_uid') == mid:
        abort(401)

    db = g.conn
    name = request.form['name']
    description = request.form['description']
    price = request.form['price']
    uid = mid
    cid = request.form['category']
    try:
        db.execute('insert into dishes(dname, description, price, uid, cid) values (%s, %s, %s, %s, %s)',
         [name, description, price, uid, cid])
        flash('Dish added!')
    except AttributeError:
        error = 'FATAL:  remaining connection slots are reserved for non-replication superuser connections'
        flash(error)
    except Exception as e:
        error = e
        flash(error)

    return redirect(url_for('merchants_dishes', uid=uid))

@app.route('/dishes/<mid>/<did>/update/', methods=['POST'])
def dishes_update(mid=None, did=None):
    if not session.get('logged_in_uid') == mid:
        abort(401)

    db = g.conn
    name = request.form['name']
    description = request.form['description']
    price = request.form['price']
    uid = mid
    cid = request.form['category']
    try:
        db.execute('update dishes set dname=(%s), description=(%s), price=(%s), uid=(%s), cid=(%s) where did=(%s)',
         [name, description, price, uid, cid, did])
        flash('Dish updated!')
    except AttributeError:
        error = 'FATAL:  remaining connection slots are reserved for non-replication superuser connections'
        flash(error)
    except Exception as e:
        error = e
        flash(error)

    return redirect(url_for('merchants_dishes', uid=uid))

@app.route('/dishes/<mid>/<did>/reviews/add/', methods=['POST'])
def reviews_add(mid=None, did=None):
    if not session.get('logged_in_as') == 'client':
        abort(401)

    db = g.conn
    uid = session.get('logged_in_uid')
    rating = request.form['rating']
    comment = request.form['comment']
    try:
        db.execute('insert into reviews(uid, did, rating, comment) values (%s, %s, %s, %s)',
                     [uid, did, rating, comment])
        flash('Review is successful!')
    except AttributeError:
        flash('FATAL:  remaining connection slots are reserved for non-replication superuser connections')
    except Exception as e:
        flash(e)

    return redirect(url_for('merchants', uid=mid))

##### User login / logout
@app.route('/login/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        db = g.conn
        try:
            clients = [r['uid'] for r in db.execute('select uid from clients').fetchall()]
            merchants = [r['uid'] for r in db.execute('select uid from merchants').fetchall()]
            if int(request.form['username']) in clients:
                session['logged_in'] = True
                session['logged_in_as'] = 'client'
                session['logged_in_uid'] = request.form['username']
                session['logged_in_name'] = db.execute('select name from users where uid=%s',
                 request.form['username']).fetchone()['name']
            elif int(request.form['username']) in merchants:
                session['logged_in'] = True
                session['logged_in_as'] = 'merchant'
                session['logged_in_uid'] = request.form['username']
                session['logged_in_name'] = db.execute('select name from users where uid=%s',
                 request.form['username']).fetchone()['name']
            else:
                error = 'Invalid User ID'
        except AttributeError:
            error = 'FATAL:  remaining connection slots are reserved for non-replication superuser connections'
        except Exception as e:
            error = e

    return render_template('index.html', error=error)

@app.route('/logout/')
def logout():
    session.pop('logged_in', None)
    session.pop('logged_in_as', None)
    session.pop('logged_in_uid', None)
    session.pop('logged_in_name', None)
    flash('You were logged out')
    return redirect(url_for('index'))

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using
        python server.py
    Show the help text using
        python server.py --help
    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
