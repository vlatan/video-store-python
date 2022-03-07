
from flask import render_template, url_for, flash
from flask import redirect, Blueprint, current_app, make_response
from app import db
from app.models import Page
from app.pages.forms import PageForm
from app.helpers import admin_required

pages = Blueprint('pages', __name__)


@pages.route('/page/new', methods=['GET', 'POST'])
@admin_required
def new_page():
    form = PageForm()
    if form.validate_on_submit():
        page = Page(title=form.title.data, content=form.content.data)
        db.session.add(page)
        flash('Your page has been created!', 'success')
        return render_template('page.html', page=page)
    return render_template('form.html', title='Add New Page',
                           form=form, legend='New Page')


@pages.route('/page/<int:page_id>/')
def page(page_id):
    page = Page.query.get_or_404(page_id)
    return render_template('page.html', page=page)


@pages.route('/page/<int:page_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_page(page_id):
    page = Page.query.get_or_404(page_id)
    form = PageForm()
    form.title.data, form.content.data = page.title, page.text
    if form.validate_on_submit():
        page = Page(title=form.title.data, content=form.content.data)
        db.session.add(page)
        flash('Your page has been updated!', 'success')
        return render_template('page.html', page=page)
    return render_template('form.html', title='Edit This Page',
                           form=form, legend='Edit Page')
