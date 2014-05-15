ENVROOT = env


all: develop

clean:
	rm -rf *.egg *.egg-info *.pyc build dist docs/_build
	find mirai -iname '*.pyc' | xargs rm

clean-env: clean
	rm -rf env

environment:
	test -d $(ENVROOT) || virtualenv $(ENVROOT)
	. $(ENVROOT)/bin/activate; $(ENVROOT)/bin/pip install -r requirements.txt

develop: environment
	. $(ENVROOT)/bin/activate; python setup.py develop

test: environment
	. $(ENVROOT)/bin/activate; python setup.py test

upload: test
	python setup.py sdist upload

docs: environment test
	. $(ENVROOT)/bin/activate; cd docs; make html
