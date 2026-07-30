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
import { reactive, watch } from 'vue'
import { Dialog, FormControl, Switch, call, toast } from 'frappe-ui'

import CatalogImageInput from '@/components/CatalogImageInput.vue'

export interface CollectionRow {
	name: string
	title: string
	slug: string
	description: string | null
	image: string | null
	published: number
	ranking: number
	product_count: number
}

const props = defineProps<{ editRow: CollectionRow | null }>()

const show = defineModel<boolean>({ required: true })
const emit = defineEmits<{ saved: [] }>()

const form = reactive({
	title: '',
	description: '',
	image: '',
	ranking: 0,
	published: true,
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
