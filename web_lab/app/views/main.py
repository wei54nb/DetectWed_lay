from flask import Blueprint, render_template, redirect, url_for
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """首页路由"""
    logger.info("访问首页")
    return render_template('index.html')

@main_bp.route('/about')
def about():
    """关于页面路由"""
    logger.info("访问关于页面")
    return render_template('about.html')

@main_bp.route('/contact')
def contact():
    """联系页面路由"""
    logger.info("访问联系页面")
    return render_template('contact.html')