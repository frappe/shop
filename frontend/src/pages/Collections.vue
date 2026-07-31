<template>
	<div class="mx-auto max-w-5xl px-6 py-8">
		<div class="flex items-center justify-between">
			<h1 class="text-xl font-semibold text-ink-gray-9">Collections</h1>
			<Button variant="solid" @click="openNew">
				<template #prefix><LucidePlus class="size-4" /></template>
				New collection
			</Button>
		</div>

		<CatalogListState
			:loading="collections.loading && !collections.data"
			:error="collections.error"
			:empty="!rows.length"
			empty-title="No collections yet"
			empty-subtitle="Group products into collections to organise your storefront."
			@retry="collections.reload()"
		>
			<template #action>
				<Button variant="solid" @click="openNew">New collection</Button>
			</template>
		</CatalogListState>

		<div v-if="rows.length && !collections.error" class="mt-6 overflow-hidden rounded-lg border border-outline-gray-1">
			<table class="w-full text-base">
				<thead>
					<tr class="border-b border-outline-gray-1 text-left text-sm text-ink-gray-5">
						<th class="w-14 px-3 py-2 font-normal"></th>
						<th class="px-3 py-2 font-normal">Collection</th>
						<th class="px-3 py-2 text-right font-normal">Products</th>
						<th class="px-3 py-2 text-right font-normal">Published</th>
						<th class="w-10 px-1 py-2"></th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="row in rows"
						:key="row.name"
						class="cursor-pointer border-b border-outline-gray-1 last:border-b-0 hover:bg-surface-gray-1"
						@click="openEdit(row.name)"
					>
						<td class="px-3 py-2">
							<div
								class="flex size-9 items-center justify-center overflow-hidden rounded border border-outline-gray-1 bg-surface-gray-1"
							>
								<img v-if="row.image" :src="row.image" :alt="row.title" class="size-full object-cover" />
								<LucideFolderOpen v-else class="size-4 text-ink-gray-4" />
							</div>
						</td>
						<td class="px-3 py-2">
							<div class="font-medium text-ink-gray-8">{{ row.title }}</div>
							<div class="text-sm text-ink-gray-5">/{{ row.slug }}</div>
						</td>
						<td class="px-3 py-2 text-right text-ink-gray-7">{{ row.product_count }}</td>
						<td class="px-3 py-2 text-right" @click.stop>
							<Switch
								:model-value="!!row.published"
								@update:model-value="(value: boolean) => togglePublished(row, value)"
							/>
						</td>
						<td class="px-1 py-2" @click.stop>
							<Dropdown :options="rowActions(row)">
								<Button variant="ghost">
									<template #icon><LucideEllipsisVertical class="size-4" /></template>
								</Button>
							</Dropdown>
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<CollectionDialog v-model="showDialog" :edit-row="editRow" @saved="collections.reload()" />
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Dropdown, Switch, call, createResource, dialog, toast } from 'frappe-ui'

import LucideEllipsisVertical from '~icons/lucide/ellipsis-vertical'
import LucideFolderOpen from '~icons/lucide/folder-open'
import LucidePencil from '~icons/lucide/pencil'
import LucidePlus from '~icons/lucide/plus'
import LucideTrash2 from '~icons/lucide/trash-2'

import CatalogListState from '@/components/CatalogListState.vue'
import CollectionDialog, { type CollectionRow } from '@/components/CollectionDialog.vue'

const showDialog = ref(false)
const editRow = ref<CollectionRow | null>(null)

const collections = createResource({
	url: 'shop.api.products.get_collections',
	auto: true,
})

const rows = computed<CollectionRow[]>(() => collections.data || [])

function openNew() {
	editRow.value = null
	showDialog.value = true
}

function openEdit(name: string) {
	editRow.value = rows.value.find((row) => row.name === name) || null
	showDialog.value = true
}

function rowActions(row: CollectionRow) {
	return [
		{ label: 'Edit', icon: LucidePencil, onClick: () => openEdit(row.name) },
		{ label: 'Delete', icon: LucideTrash2, theme: 'red', onClick: () => confirmDelete(row) },
	]
}

function confirmDelete(row: CollectionRow) {
	dialog.confirm({
		title: 'Delete collection',
		message: `Delete <b>${row.title}</b>? Products in it are kept.`,
		theme: 'red',
		confirmLabel: 'Delete',
		onConfirm: async () => {
			await call('shop.api.products.delete_collection', { name: row.name })
			toast.success('Collection deleted')
			collections.reload()
		},
	})
}

async function togglePublished(row: CollectionRow, value: boolean) {
	row.published = value ? 1 : 0
	try {
		await call('shop.api.products.save_collection', {
			payload: {
				name: row.name,
				title: row.title,
				description: row.description,
				image: row.image,
				ranking: row.ranking,
				published: row.published,
			},
		})
	} catch (error) {
		row.published = value ? 0 : 1
		toast.error('Could not update collection')
	}
}
</script>
