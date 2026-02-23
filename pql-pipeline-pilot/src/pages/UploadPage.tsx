import { CsvUploader } from '@/components/CsvUploader';

export default function UploadPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Upload PQL Data</h1>
        <p className="text-sm text-muted-foreground">Import a CSV file with your PQL data to start the pipeline</p>
      </div>
      <CsvUploader />
    </div>
  );
}
