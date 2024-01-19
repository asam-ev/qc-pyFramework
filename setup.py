from setuptools import setup

setup(name='OpenValidator',
        version='0.0.1',
        description='Validator for ASAM OpenX Standard files.',
        url='#',
        author='Mirco Nierenz',
        author_email='Mirco.Nierenz@triangraphics.de',
        license='TBD',
        packages=['OpenValidator'],
        zip_safe=False,
        install_requires=['lxml', 'scipy'])
