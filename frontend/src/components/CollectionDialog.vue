<template>
	<Dialog
		v-model="show"
		:options="{
			title: editName ? 'Edit collection' : 'New collection',
			actions: [
				{
					label: editName ? 'Save' : 'Create',
					variant: 'solid',
					onClick: save,
				},
			],
		}"
	>
		<div class="space-y-4">
			<div v-if="editName">
				<div class="text-sm text-ink-gray-5">Slug</div>
				<div class="mt-1 text-base text-ink-gray-7">{{ form.slug || 'Not set' }}</div>
			</div>
			<FormControl v-model="form.title" label="Title" />
			<FormControl v-model="form.description" type="textarea" label="Description" />
			<FormControl v-if="editName" v-model="form.ranking" type="number" label="Ranking" />
			<FormControl v-model="form.published" type="checkbox" label="Published" />
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { Dialog, FormControl, call, createListResource, toast } from 'frappe-ui'

const props = defineProps<{
	editName: string | null
	list: ReturnType<typeof createListResource>
}>()

const show = defineModel<boolean>({ required: true })

const form = reactive({
	title: '',
	description: '',
	published: false,
	ranking: 0,
	slug: '',
})

watch(show, (open) => {
	if (open) resetAndLoad()
})

async function resetAndLoad() {
	Object.assign(form, { title: '', description: '', published: false, ranking: 0, slug: '' })
	if (!props.editName) return
	const doc = await call('frappe.client.get', {
		doctype: 'Shop Collection',
		name: props.editName,
	})
	Object.assign(form, {
		title: doc.title || '',
		description: doc.description || '',
		published: !!doc.published,
		ranking: doc.ranking || 0,
		slug: doc.slug || '',
	})
}

async function save() {
	if (!form.title.trim()) {
		toast.error('Title is required')
		return
	}
	try {
		if (props.editName) {
			await props.list.setValue.submit({
				name: props.editName,
				title: form.title,
				description: form.description,
				published: form.published ? 1 : 0,
				ranking: Number(form.ranking) || 0,
			})
			toast.success('Collection updated')
		} else {
			await props.list.insert.submit({
				title: form.title,
				description: form.description,
				published: form.published ? 1 : 0,
			})
			toast.success('Collection created')
		}
		show.value = false
	} catch (error) {
		toast.error('Could not save collection')
	}
}
</script>
