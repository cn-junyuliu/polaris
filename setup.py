from setuptools import setup

def readme():
    with open('README.md') as f:
        return f.read()

setup(name='polaris',
      version='0.1',
      description='Polarized microscope simulation tool.',
      long_description=readme(),
      classifiers=[
          'Development Status :: 2 - Pre-Alpha',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: MIT License',
          'Natural Language :: English',
          'Programming Language :: Python :: 3.5',
          'Topic :: Scientific/Engineering :: Physics',
      ],
      url='https://github.com/talonchandler/polaris',
      author='Talon Chandler',
      author_email='talonchandler@talonchandler.com',
      license='MIT',
      packages=['polaris', 'polaris.harmonics', 'polaris.micro'],
      include_package_data=True,
      zip_safe=False,
      test_suite='tests',
      install_requires=[
          'numpy',
          'matplotlib',
          'scipy',
          'sympy',
          'pytest',
          'setuptools-git',
          'imageio',
          'vtk',
          'tifffile',
          'imagecodecs',
          'joblib',
          'dipy==1.4.1',
          'fury==0.7.1',
      ]
      )
