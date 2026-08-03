import LucideBoxes from '~icons/lucide/boxes'
import LucideFolderOpen from '~icons/lucide/folder-open'
import LucideHouse from '~icons/lucide/house'
import LucideMap from '~icons/lucide/map'
import LucidePackage from '~icons/lucide/package'
import LucideSettings from '~icons/lucide/settings'
import LucideShoppingBasket from '~icons/lucide/shopping-basket'
import LucideShoppingCart from '~icons/lucide/shopping-cart'
import LucideSparkles from '~icons/lucide/sparkles'
import LucideStar from '~icons/lucide/star'
import LucideTicketPercent from '~icons/lucide/ticket-percent'
import LucideTruck from '~icons/lucide/truck'
import LucideUndo2 from '~icons/lucide/undo-2'
import LucideUsers from '~icons/lucide/users'

export const navGroups = [
	{
		label: 'Assistant',
		items: [
			{ label: 'Assistant', route: '/assistant', icon: LucideSparkles },
			{ label: 'Walkthroughs', route: '/walkthroughs', icon: LucideMap },
		],
	},
	{
		label: 'Overview',
		items: [{ label: 'Dashboard', route: '/', icon: LucideHouse }],
	},
	{
		label: 'Orders',
		items: [
			{ label: 'Orders', route: '/orders', icon: LucideShoppingCart },
			{ label: 'Fulfillments', route: '/fulfillments', icon: LucideTruck },
			{ label: 'Returns', route: '/returns', icon: LucideUndo2 },
			{ label: 'Customers', route: '/customers', icon: LucideUsers },
			{ label: 'Carts', route: '/carts', icon: LucideShoppingBasket },
		],
	},
	{
		label: 'Catalog',
		items: [
			{ label: 'Products', route: '/products', icon: LucidePackage },
			{ label: 'Inventory', route: '/inventory', icon: LucideBoxes },
			{ label: 'Collections', route: '/collections', icon: LucideFolderOpen },
			{ label: 'Reviews', route: '/reviews', icon: LucideStar },
		],
	},
	{
		label: 'Marketing',
		items: [{ label: 'Discounts', route: '/discounts', icon: LucideTicketPercent }],
	},
	{
		label: 'Store',
		items: [{ label: 'Settings', route: '/settings', icon: LucideSettings }],
	},
]
