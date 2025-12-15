export class Recorder {
	chunks: BlobPart[] = [];
	mediaRecorder: MediaRecorder | null = null;

	constructor(stream: MediaStream) {
		this.mediaRecorder = new MediaRecorder(stream);
		this.mediaRecorder.ondataavailable = (event) => {
			this.chunks.push(event.data);
		};
	}

	start() {
		this.chunks = [];
		this.mediaRecorder?.start();
	}

	stop(): Promise<Blob> {
		return new Promise((resolve) => {
			if (!this.mediaRecorder) {
				throw new Error('MediaRecorder not initialized');
			}

			this.mediaRecorder.onstop = () => {
				const blob = new Blob(this.chunks, { type: 'audio/webm' });
				resolve(blob);
			};
			this.mediaRecorder.stop();
		});
	}
}
