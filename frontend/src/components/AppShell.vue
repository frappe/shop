<template>
	<div class="flex h-screen w-screen bg-surface-base">
		<aside class="flex w-56 shrink-0 flex-col border-r border-outline-gray-1 bg-surface-menu-bar">
			<div class="flex items-center gap-2 px-4 py-4">
				<img src="/shop-logo.svg" alt="Shop" class="size-6 rounded" />
				<span class="text-lg font-semibold text-ink-gray-9">Shop</span>
			</div>
			<nav class="flex flex-1 flex-col gap-4 overflow-y-auto px-2 pb-4">
				<div v-for="group in navGroups" :key="group.label">
					<div class="px-2 pb-1 text-xs font-medium uppercase tracking-wide text-ink-gray-4">
						{{ group.label }}
					</div>
					<div class="flex flex-col gap-0.5">
						<router-link
							v-for="item in group.items"
							:key="item.route"
							:to="item.route"
							class="flex items-center gap-2 rounded px-2 py-1.5 text-base text-ink-gray-7 transition hover:bg-surface-gray-2"
							:class="{ 'bg-surface-selected text-ink-gray-9 shadow-sm': isActive(item) }"
						>
							<component :is="item.icon" class="size-4 text-ink-gray-6" />
							{{ item.label }}
						</router-link>
					</div>
				</div>
			</nav>
			<div class="border-t border-outline-gray-1 px-4 py-3">
				<div class="truncate text-sm text-ink-gray-7">{{ session.user }}</div>
				<button class="mt-1 text-sm text-ink-gray-5 hover:text-ink-gray-8" @click="session.logout">
					Log out
				</button>
			</div>
		</aside>
		<div class="flex min-w-0 flex-1 flex-col">
			<header
				class="flex h-12 shrink-0 items-center justify-end gap-2 border-b border-outline-gray-1 px-4"
			>
				<Button link="/">
					<template #prefix>
						<LucideExternalLink class="size-4" />
					</template>
					View store
				</Button>
				<Button link="/builder">Edit in Builder</Button>
			</header>
			<main class="flex-1 overflow-y-auto">
				<router-view />
			</main>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

import LucideBoxes from '~icons/lucide/boxes'
import LucideExternalLink from '~icons/lucide/external-link'
import LucideFolderOpen from '~icons/lucide/folder-open'
import LucideHouse from '~icons/lucide/house'
import LucidePackage from '~icons/lucide/package'
import LucideSettings from '~icons/lucide/settings'
import LucideShoppingBasket from '~icons/lucide/shopping-basket'
import LucideShoppingCart from '~icons/lucide/shopping-cart'
import LucideSparkles from '~icons/lucide/sparkles'
import LucideStar from '~icons/lucide/star'
import LucideTicketPercent from '~icons/lucide/ticket-percent'
import LucideTruck from '~icons/lucide/truck'
import LucideUsers from '~icons/lucide/users'

import { session } from '@/stores/session'

const route = useRoute()

const navGroups = [
	{
		label: 'Assistant',
		items: [{ label: 'Assistant', route: '/assistant', icon: LucideSparkles }],
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
			{ label: 'Customers', route: '/customers', icon: LucideUsers },
			{ label: 'Abandoned carts', route: '/carts', icon: LucideShoppingBasket },
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

const isActive = (item: { route: string }) => {
	if (item.route === '/') return route.path === '/'
	return route.path.startsWith(item.route)
}
</script>
