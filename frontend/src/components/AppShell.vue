<template>
	<div class="flex h-screen w-screen bg-surface-base">
		<aside class="flex w-56 shrink-0 flex-col border-r border-outline-gray-1 bg-surface-menu-bar">
			<div class="flex items-center gap-2 px-4 py-4">
				<img src="/shop-logo.svg" alt="Shop" class="size-6 rounded" />
				<span class="text-lg font-semibold text-ink-gray-9">Shop</span>
			</div>
			<nav class="flex flex-1 flex-col gap-0.5 px-2">
				<router-link
					v-for="item in navItems"
					:key="item.route"
					:to="item.route"
					class="flex items-center gap-2 rounded px-2 py-1.5 text-base text-ink-gray-7 transition hover:bg-surface-gray-2"
					:class="{ 'bg-surface-selected text-ink-gray-9 shadow-sm': isActive(item) }"
				>
					<component :is="item.icon" class="size-4 text-ink-gray-6" />
					{{ item.label }}
				</router-link>
			</nav>
			<div class="border-t border-outline-gray-1 px-4 py-3">
				<div class="truncate text-sm text-ink-gray-7">{{ session.user }}</div>
				<button class="mt-1 text-sm text-ink-gray-5 hover:text-ink-gray-8" @click="session.logout">
					Log out
				</button>
			</div>
		</aside>
		<main class="flex-1 overflow-y-auto">
			<router-view />
		</main>
	</div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

import LucideFolderOpen from '~icons/lucide/folder-open'
import LucideHouse from '~icons/lucide/house'
import LucidePackage from '~icons/lucide/package'
import LucideSettings from '~icons/lucide/settings'
import LucideShoppingCart from '~icons/lucide/shopping-cart'

import { session } from '@/stores/session'

const route = useRoute()

const navItems = [
	{ label: 'Dashboard', route: '/', icon: LucideHouse },
	{ label: 'Orders', route: '/orders', icon: LucideShoppingCart },
	{ label: 'Products', route: '/products', icon: LucidePackage },
	{ label: 'Collections', route: '/collections', icon: LucideFolderOpen },
	{ label: 'Settings', route: '/settings', icon: LucideSettings },
]

const isActive = (item: { route: string }) => {
	if (item.route === '/') return route.path === '/'
	return route.path.startsWith(item.route)
}
</script>
