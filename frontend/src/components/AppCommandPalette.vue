<template>
	<CommandPalette v-model:show="show" v-model:search-query="searchQuery" :groups="groups" @select="goTo" />
</template>

<script setup lang="ts">
import { useShortcut } from 'frappe-ui'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import CommandPalette from '@/components/CommandPalette.vue'
import CommandPaletteItem from '@/components/CommandPaletteItem.vue'
import { navGroups } from '@/utils/navigation'

const show = defineModel<boolean>('show', { default: false })

const router = useRouter()
const searchQuery = ref('')

useShortcut({
	key: 'k',
	ctrl: true,
	description: 'Open Command Palette',
	group: 'General',
	allowInInput: true,
	handler: () => {
		show.value = true
	},
})

const pages = navGroups.flatMap((group) =>
	group.items.map((item) => ({
		name: item.route,
		title: item.label,
		icon: item.icon,
		route: item.route,
	})),
)

const groups = computed(() => {
	const query = searchQuery.value.toLowerCase()
	const items = query
		? pages.filter((page) => page.title.toLowerCase().includes(query))
		: pages

	return [{ title: 'Pages', hideTitle: true, component: CommandPaletteItem, items }]
})

function goTo(item: { route: string }) {
	router.push(item.route)
}
</script>
