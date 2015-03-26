from distutils.core import setup
setup(name = "appy", version = "dev",
      description = "The Appy framework",
      long_description = "Appy builds simple but complex web Python apps.",
      author = "Gaetan Delannay",
      author_email = "gaetan.delannay AT geezteem.com",
      license = "GPL", platforms="all",
      url = 'http://appyframework.org',
      packages = ["appy","appy.fields","appy.bin","appy.gen","appy.gen.ui","appy.gen.ui.jscalendar","appy.gen.ui.jscalendar.lang","appy.gen.ui.jscalendar.skins","appy.gen.ui.jscalendar.skins.tiger","appy.gen.ui.jscalendar.skins.aqua","appy.gen.ui.ckeditor","appy.gen.templates","appy.gen.tr","appy.gen.wrappers","appy.gen.mixins","appy.px","appy.shared","appy.shared.data","appy.pod","appy.pod.test","appy.pod.test.templates","appy.pod.test.contexts","appy.pod.test.images","appy.pod.test.results"],
      package_data = {'':["*.*"]})
