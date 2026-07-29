<template>
	<div class="mx-auto max-w-4xl px-6 py-8">
		<div class="flex items-center justify-between">
			<h1 class="text-xl font-semibold text-ink-gray-9">Collections</h1>
			<Button variant="solid" @click="openNew">New collection</Button>
		</div>

		<div class="mt-6 overflow-hidden rounded-lg border border-outline-gray-1">
			<table class="w-full text-base">
				<thead>
					<tr class="border-b border-outline-gray-1 text-left text-sm text-ink-gray-5">
						<th class="px-3 py-2 font-normal">Collection</th>
						<th class="px-3 py-2 font-normal">Slug</th>
						<th class="px-3 py-2 text-right font-normal">Ranking</th>
						<th class="px-3 py-2 text-right font-normal">Published</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="row in collections.data || []"
						:key="row.name"
						class="cursor-pointer border-b border-outline-gray-1 last:border-b-0 hover:bg-surface-gray-1"
						@click="openEdit(row.name)"
					>
						<td class="px-3 py-2 font-medium text-ink-gray-8">{{ row.title }}</td>
						<td class="px-3 py-2 text-ink-gray-6">{{ row.slug }}</td>
						<td class="px-3 py-2 text-right text-ink-gray-6">{{ row.ranking }}</td>
						<td class="px-3 py-2 text-right" @click.stop>
							<Switch
								:model-value="!!row.published"
								@update:model-value="(value: boolean) => togglePublished(row.name, value)"
							/>
						</td>
					</tr>
					<tr v-if="!(collections.data || []).length">
						<td colspan="4" class="px-3 py-8 text-center text-ink-gray-5">No collections yet</td>
					</tr>
				</tbody>
			</table>
		</div>

		<CollectionDialog v-model="showDialog" :edit-name="editName" :list="collections" />
	</div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Switch, createListResource } from 'frappe-ui'

import CollectionDialog from '@/components/CollectionDialog.vue'

const showDialog = ref(false)
const editName = ref<string | null>(null)

const collections = createListResource({
	doctype: 'Shop Collection',
	fields: ['name', 'title', 'slug', 'published', 'ranking'],
	orderBy: 'ranking desc',
	pageLength: 100,
	auto: true,
})

function openNew() {
	editName.value = null
	showDialog.value = true
}

function openEdit(name: string) {
	editName.value = name
	showDialog.value = true
}

function togglePublished(name: string, value: boolean) {
	collections.setValue.submit({ name, published: value ? 1 : 0 })
}
</script>
