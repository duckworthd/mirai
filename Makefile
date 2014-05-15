ENVROOT = "env"


clean:
	rm -rf *.egg *.egg-info *.pyc build dist
	find mirai -iname '*.pyc' | xargs rm

clean-env: clean
	rm -rf env

environment:
	virtualenv $(ENVROOT)

develop: environment
	. $(ENVROOT)/bin/activate
	python setup.py develop

test: environment
	. $(ENVROOT)/bin/activate
	python setup.py test

upload: test
	python setup.py sdist upload
