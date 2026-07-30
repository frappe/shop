<template>
	<div>
		<div class="space-y-2">
			<div
				v-for="(image, index) in model"
				:key="image + index"
				class="flex items-center gap-3 rounded border border-outline-gray-1 p-2"
			>
				<img :src="image" alt="" class="size-12 shrink-0 rounded object-cover" />
				<div class="min-w-0 flex-1">
					<div class="truncate text-sm text-ink-gray-7">{{ fileName(image) }}</div>
					<Badge v-if="index === 0" theme="blue" size="sm" class="mt-0.5">Card image</Badge>
				</div>
				<div class="flex shrink-0 gap-1">
					<Button variant="ghost" :disabled="index === 0" @click="move(index, -1)">
						<template #icon><LucideChevronUp class="size-4" /></template>
					</Button>
					<Button variant="ghost" :disabled="index === model.length - 1" @click="move(index, 1)">
						<template #icon><LucideChevronDown class="size-4" /></template>
					</Button>
					<Button variant="ghost" theme="red" @click="remove(index)">
						<template #icon><LucideTrash2 class="size-4" /></template>
					</Button>
				</div>
			</div>
		</div>
		<div class="mt-2 flex items-center gap-3">
			<FileUploader :file-types="['image/*']" @success="add" @failure="onFailure">
				<template #default="{ uploading, progress, openFileSelector }">
					<Button :loading="uploading" @click="openFileSelector">
						<template #prefix><LucidePlus class="size-4" /></template>
						{{ uploading ? `Uploading ${progress}%` : 'Add image' }}
					</Button>
				</template>
			</FileUploader>
			<span class="text-sm text-ink-gray-5">The first image is used on product cards.</span>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Badge, FileUploader, toast } from 'frappe-ui'

import LucideChevronDown from '~icons/lucide/chevron-down'
import LucideChevronUp from '~icons/lucide/chevron-up'
import LucidePlus from '~icons/lucide/plus'
import LucideTrash2 from '~icons/lucide/trash-2'

const model = defineModel<string[]>({ required: true })

function fileName(url: string) {
	return url.split('/').pop()?.split('?')[0] || url
}

function add(file: { file_url: string }) {
	model.value = [...model.value, file.file_url]
}

function remove(index: number) {
	model.value = model.value.filter((_, i) => i !== index)
}

function move(index: number, delta: number) {
	const next = [...model.value]
	const [image] = next.splice(index, 1)
	next.splice(index + delta, 0, image)
	model.value = next
}

function onFailure() {
	toast.error('Could not upload image')
}
</script>
