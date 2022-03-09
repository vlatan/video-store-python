
from flask import redirect, render_template, flash, url_for, Blueprint
from app import db
from app.models import Page
from app.pages.forms import PageForm
from app.helpers import admin_required

pages = Blueprint('pages', __name__)


@pages.route('/page/<int:id>/')
def page(id):
    page = Page.query.get_or_404(id)
    return render_template('page.html', page=page)


@pages.route('/page/new', methods=['GET', 'POST'])
@admin_required
def new_page():
    form = PageForm()
    if form.validate_on_submit():
        page = Page(title=form.title.data, content=form.content.data)
        db.session.add(page)
        db.session.commit()
        flash('Your page has been created!', 'success')
        return redirect(url_for('pages.page', id=page.id))
    return render_template('form.html', title='Add New Page',
                           form=form, legend='New Page')


@pages.route('/page/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_page(id):
    page = Page.query.get_or_404(id)
    form = PageForm()
    if form.validate_on_submit():
        page.title, page.content = form.title.data, form.content.data
        db.session.commit()
        page.delete_cache()
        flash('Your page has been updated!', 'success')
        return redirect(url_for('pages.page', id=page.id))
    form.title.data, form.content.data = page.title, page.content
    return render_template('form.html', title='Edit This Page',
                           form=form, legend='Edit Page')
