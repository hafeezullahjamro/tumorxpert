export default function HelpPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-primary">Help - Model Card</h1>
      <section className="space-y-4 rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-900">Model status</h2>
        <p className="text-sm text-slate-600">
          TumorXpert runs a local workflow with DICOM or BraTS-style intake, preprocessing, optional missing-modality synthesis, and
          dual-model segmentation on the completed four-modality set. The final exported result is the ensemble output built from nnU-Net
          and Swin UNETR predictions. Keep the research-only warning in mind and validate outputs before any downstream use.
        </p>
      </section>

      <section className="space-y-3 rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-900">FAQ</h2>
        <div>
          <h3 className="font-semibold text-slate-800">Is this clinical?</h3>
          <p className="text-sm text-slate-600">No. Research demo only. Do not use for diagnosis or patient management.</p>
        </div>
        <div>
          <h3 className="font-semibold text-slate-800">Where are files stored?</h3>
          <p className="text-sm text-slate-600">
            Under <code>./storage</code>. Uploads, processed outputs, and exports are separated for clarity. Auto-delete rules keep disk usage
            tidy.
          </p>
        </div>
        <div>
          <h3 className="font-semibold text-slate-800">How do I integrate my model?</h3>
          <p className="text-sm text-slate-600">
            The runtime is wired through <code>backend/app/services/inference_pipeline.py</code> and <code>backend/app/services/model_defs.py</code>.
            Update those modules if you retrain checkpoints, adjust ensemble behavior, or change preprocessing rules.
          </p>
        </div>
      </section>

      <section className="space-y-3 rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-900">Limitations</h2>
        <ul className="list-disc pl-6 text-sm text-slate-600">
          <li>Research-use only. This is not a cleared clinical workflow.</li>
          <li>DICOM ZIP support depends on modality metadata being readable and mappable to FLAIR, T1, T1ce, and T2.</li>
          <li>Only one missing modality can be synthesised automatically per study.</li>
          <li>No DICOMweb adapter yet. Attachments stream from disk using simple endpoints.</li>
          <li>Brush editing remains mocked client-side only.</li>
        </ul>
      </section>
    </div>
  );
}
