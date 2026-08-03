<template>
	<div class="flex h-screen w-screen bg-surface-base">
		<aside class="flex w-56 shrink-0 flex-col border-r border-outline-gray-1 bg-surface-menu-bar">
			<div class="flex items-center gap-2 px-4 py-4">
				<img src="/shop-logo.svg" alt="Shop" class="size-6 rounded" />
				<span class="text-lg font-semibold text-ink-gray-9">Shop</span>
			</div>
			<div class="flex flex-col gap-0.5 px-2 pb-4">
				<button
					class="flex items-center justify-between rounded px-2 py-1.5 text-base text-ink-gray-7 transition hover:bg-surface-gray-2"
					@click="showCommandPalette = true"
				>
					<span class="flex items-center gap-2">
						<span class="lucide-search size-4 text-ink-gray-6" />
						Search
					</span>
					<KeyboardShortcut combo="Mod+K" />
				</button>
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
							<span :class="item.icon" class="size-4 text-ink-gray-6" />
							{{ item.label }}
						</router-link>
						<a
							v-if="group.label === 'Store'"
							href="/"
							target="_blank"
							rel="noreferrer noopener"
							class="flex items-center gap-2 rounded px-2 py-1.5 text-base text-ink-gray-7 transition hover:bg-surface-gray-2"
						>
							<span class="lucide-external-link size-4 text-ink-gray-6" />
							View store
						</a>
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
		<main class="min-w-0 flex-1 overflow-y-auto [scrollbar-gutter:stable]">
			<router-view />
		</main>
	</div>
	<AppCommandPalette v-model:show="showCommandPalette" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'

import { KeyboardShortcut } from 'frappe-ui'

import AppCommandPalette from '@/components/AppCommandPalette.vue'
import { session } from '@/stores/session'
import { navGroups } from '@/utils/navigation'

const route = useRoute()
const showCommandPalette = ref(false)

const isActive = (item: { route: string }) => {
	if (item.route === '/') return route.path === '/'
	return route.path.startsWith(item.route)
}
</script>
