"""A site theme: what a site changes in one of Shop's theme generators."""

from typing import ClassVar

from shop.theme_generators.blocks import component_ref


class Theme:
	"""What a site theme changes in a generator; pass one to the generator's generate(). Anything left
	unset keeps the generator's own, so a site theme holds only what makes it different.

	title: the theme's display name, used in its components' names (e.g. "Acme Store Navbar").
	group: the theme's name: its template group, variables and styles are named after it.
	head, body, mono: the heading, body and label fonts (mono is used by generators that have one).
	palette: colours, {name: (light, dark)}, using the generator's palette keys.
	skip_routes: pages the site already has, which the theme leaves out (e.g. "about").
	component_ids: the generator's component id -> the theme's own id, e.g. {"shop-navbar": "acme-bar"};
	  the others are named after the theme's group (shop-hero -> acme-hero).
	site_components: ids among those that the site already has (e.g. its own footer); they are
	  placed on the pages but not generated.
	header_component: a site component placed above every page (e.g. the site's header).
	blocks: builder name -> function(refs) returning the block to use instead of the generator's,
	  for its components (nav, footer, hero, trust_row, delivery_card, ...) and pages
	  (home_blocks, product_blocks, ...).
	faqs: (question, answer) pairs for the FAQ page.
	listing_subtitle: the line under the product listing's heading.
	product_description: where the product page shows the description: "beside" the images, in
	  the buy box column, or "below" them at full width, the images staying in view while scrolling.
	extra_css: added after the generator's styles.
	"""

	defaults: ClassVar[dict] = {}

	def __init__(
		self,
		group=None,
		title=None,
		head=None,
		body=None,
		mono=None,
		palette=None,
		skip_routes=(),
		component_ids=None,
		site_components=(),
		header_component=None,
		blocks=None,
		faqs=None,
		listing_subtitle=None,
		product_description="beside",
		extra_css="",
	):
		self.group = group or self.defaults["group"]
		self.title = title or self.group.title()
		self.head = head or self.defaults["head"]
		self.body = body or self.defaults["body"]
		self.mono = mono or self.defaults.get("mono") or "monospace"
		self.palette = {**self.defaults["palette"], **(palette or {})}
		self.skip_routes = set(skip_routes)
		self.component_ids = component_ids or {}
		self.site_components = set(site_components)
		self.header_component = header_component
		self.blocks = blocks or {}
		self.faqs = faqs
		self.listing_subtitle = listing_subtitle
		self.product_description = product_description
		self.extra_css = extra_css

	def build(self, name, default, refs):
		return self.blocks.get(name, default)(refs)

	def component_id(self, component_id):
		"""The theme's id for one of the generator's components: its own id when it gives one, else,
		for a theme with its own group, the generator's id under that group (shop-hero -> acme-hero),
		so a site theme never writes over the generator's own components."""
		if component_id in self.component_ids:
			return self.component_ids[component_id]
		if self.group == self.defaults["group"]:
			return component_id
		return f"{self.group}-{component_id.split('-', 1)[1]}"

	def component_ref(self, component_id):
		"""A component placed on a page: the theme's own id for it when it has one."""
		return component_ref(self.component_id(component_id))

	def header(self):
		return [component_ref(self.header_component)] if self.header_component else []

	def components(self, components, refs):
		"""(id, name, block) for each of the generator's components the theme generates. `components`
		holds (id, name, builder name, default builder); a component the theme renames is named after it."""
		for component_id, name, builder, default in components:
			theme_id = self.component_id(component_id)
			if theme_id in self.site_components:
				continue
			if theme_id != component_id:
				name = f"{self.title} Store {name.split(' ', 1)[1]}"
			yield theme_id, name, self.build(builder, default, refs)
