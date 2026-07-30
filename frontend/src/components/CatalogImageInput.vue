<template>
	<div>
		<div v-if="label" class="mb-1.5 text-xs text-ink-gray-5">{{ label }}</div>
		<div class="flex items-center gap-3">
			<div
				class="flex size-14 shrink-0 items-center justify-center overflow-hidden rounded border border-outline-gray-1 bg-surface-gray-1"
			>
				<img v-if="model" :src="model" :alt="label || 'Image'" class="size-full object-cover" />
				<LucideImage v-else class="size-5 text-ink-gray-4" />
			</div>
			<FileUploader :file-types="['image/*']" @success="onUpload" @failure="onFailure">
				<template #default="{ uploading, progress, openFileSelector }">
					<Button :loading="uploading" @click="openFileSelector">
						{{ uploading ? `Uploading ${progress}%` : model ? 'Replace' : 'Upload' }}
					</Button>
				</template>
			</FileUploader>
			<Button v-if="model" variant="ghost" theme="red" @click="model = ''">Remove</Button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { FileUploader, toast } from 'frappe-ui'

import LucideImage from '~icons/lucide/image'

defineProps<{ label?: string }>()

const model = defineModel<string>({ default: '' })

function onUpload(file: { file_url: string }) {
	model.value = file.file_url
}

function onFailure() {
	toast.error('Could not upload image')
}
</script>
