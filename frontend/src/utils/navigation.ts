export const navGroups = [
	{
		label: 'Assistant',
		items: [
			{ label: 'Assistant', route: '/assistant', icon: 'lucide-sparkles' },
			{ label: 'Walkthroughs', route: '/walkthroughs', icon: 'lucide-map' },
		],
	},
	{
		label: 'Overview',
		items: [{ label: 'Dashboard', route: '/', icon: 'lucide-house' }],
	},
	{
		label: 'Orders',
		items: [
			{ label: 'Orders', route: '/orders', icon: 'lucide-shopping-cart' },
			{ label: 'Fulfillments', route: '/fulfillments', icon: 'lucide-truck' },
			{ label: 'Returns', route: '/returns', icon: 'lucide-undo-2' },
			{ label: 'Customers', route: '/customers', icon: 'lucide-users' },
			{ label: 'Trade accounts', route: '/trade-accounts', icon: 'lucide-briefcase' },
			{ label: 'Carts', route: '/carts', icon: 'lucide-shopping-basket' },
		],
	},
	{
		label: 'Catalog',
		items: [
			{ label: 'Products', route: '/products', icon: 'lucide-package' },
			{ label: 'Inventory', route: '/inventory', icon: 'lucide-boxes' },
			{ label: 'Collections', route: '/collections', icon: 'lucide-folder-open' },
			{ label: 'Item Groups', route: '/item-groups', icon: 'lucide-folder-tree' },
			{ label: 'Specifications', route: '/specifications', icon: 'lucide-list-checks' },
			{ label: 'Reviews', route: '/reviews', icon: 'lucide-star' },
		],
	},
	{
		label: 'Marketing',
		items: [{ label: 'Discounts', route: '/discounts', icon: 'lucide-ticket-percent' }],
	},
	{
		label: 'Store',
		items: [{ label: 'Settings', route: '/settings', icon: 'lucide-settings' }],
	},
]
