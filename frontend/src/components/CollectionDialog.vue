<template>
	<Dialog
		v-model="show"
		:options="{
			title: editRow ? 'Edit collection' : 'New collection',
			actions: [{ label: editRow ? 'Save' : 'Create', variant: 'solid', onClick: save }],
		}"
	>
		<div class="space-y-4">
			<FormControl v-model="form.title" label="Title" required />
			<div v-if="editRow" class="text-sm text-ink-gray-5">
				Storefront URL: /collection/{{ editRow.slug }}
			</div>
			<FormControl v-model="form.description" type="textarea" :rows="3" label="Description" />
			<CatalogImageInput v-model="form.image" label="Image" />
			<UiPicker
				v-model="form.parent_collection"
				label="Inside"
				:options="parentOptions"
				description="Show this collection inside another, e.g. Temperature sensors inside Sensors"
			/>
			<UiPicker
				v-model="form.item_group"
				label="Include Item Group"
				:options="itemGroupOptions"
				description="Its products, and those of the groups inside it, are in the collection without adding them one by one."
			/>
			<FormControl
				v-model.number="form.ranking"
				type="number"
				label="Ranking"
				description="Higher ranked collections appear first"
				class="w-40"
			/>
			<Switch v-model="form.published" label="Published" class="!w-auto" />
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { Dialog, FormControl, Switch, call, createResource, toast } from 'frappe-ui'

import CatalogImageInput from '@/components/CatalogImageInput.vue'
import UiPicker from '@/components/UiPicker.vue'

export interface CollectionRow {
	name: string
	title: string
	slug: string
	description: string | null
	image: string | null
	published: number
	ranking: number
	product_count: number
	parent_collection: string | null
	parent_title: string | null
	item_group: string | null
}

const props = defineProps<{ editRow: CollectionRow | null; collections: CollectionRow[] }>()

// any other collection, except those already inside this one
const parentOptions = computed(() => {
	const inside = new Set<string>()
	if (props.editRow) {
		inside.add(props.editRow.name)
		let added = true
		while (added) {
			added = false
			for (const row of props.collections) {
				if (row.parent_collection && inside.has(row.parent_collection) && !inside.has(row.name)) {
					inside.add(row.name)
					added = true
				}
			}
		}
	}
	return [
		{ label: 'None (top level)', value: '' },
		...props.collections.filter((row) => !inside.has(row.name)).map((row) => ({ label: row.title, value: row.name })),
	]
})

const itemGroups = createResource({ url: 'shop.api.products.get_item_group_tree', auto: true })
const itemGroupOptions = computed(() => [
	{ label: 'None', value: '' },
	...(itemGroups.data || []).map((group: { name: string; depth: number }) => ({
		label: `${'\u00a0\u00a0'.repeat(group.depth - 1)}${group.name}`,
		value: group.name,
	})),
])

const show = defineModel<boolean>({ required: true })
const emit = defineEmits<{ saved: [] }>()

const form = reactive({
	title: '',
	description: '',
	image: '',
	ranking: 0,
	published: true,
	parent_collection: '',
	item_group: '',
})

watch(show, (open) => {
	if (open) reset()
})

function reset() {
	Object.assign(form, {
		title: props.editRow?.title || '',
		description: props.editRow?.description || '',
		image: props.editRow?.image || '',
		ranking: props.editRow?.ranking || 0,
		published: props.editRow ? !!props.editRow.published : true,
		parent_collection: props.editRow?.parent_collection || '',
		item_group: props.editRow?.item_group || '',
	})
}

async function save() {
	if (!form.title.trim()) {
		toast.error('Title is required')
		return
	}
	try {
		await call('shop.api.products.save_collection', {
			payload: { name: props.editRow?.name, ...form },
		})
		toast.success(props.editRow ? 'Collection saved' : 'Collection created')
		show.value = false
		emit('saved')
	} catch (error) {
		const messages = (error as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not save collection')
	}
}
</script>
