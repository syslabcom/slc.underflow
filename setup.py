from setuptools import setup, find_packages

version = '4.0-P3-1'

setup(
    name='slc.underflow',
    version=version,
    description="A question/answer product",
    long_description=open("README.txt").read(),
    # Get more strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Programming Language :: Python",
        ],
    keywords='question answer comments',
    author='Izak Burger, Syslab GmbH',
    author_email='isburger@gmail.com',
    url='https://github.com/syslabcom/slc.underflow',
    license='GPL',
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['slc'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'setuptools',
        'Products.CMFPlone',
        'Products.UserAndGroupSelectionWidget',
        'plone.principalsource',
        'slc.mailrouter',
        'slc.stickystatusmessages',
        'plone.app.dexterity',
        'plone.app.referenceablebehavior',
    ],
    entry_points="""
        [z3c.autoinclude.plugin]
        target = plone
    """,
    setup_requires=["PasteScript"],
    paster_plugins = ["ZopeSkel"],
    )
