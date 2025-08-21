"use client";
type Props = { loterieId: string };

export default function VerificationBlocs({ loterieId }: Props) {
  return (
    <div className="p-4 rounded border mt-6">
      <h2 className="font-semibold mb-2">Vérifier des blocs</h2>
      <p className="text-sm text-gray-600">
        Loterie sélectionnée : <span className="font-mono">{loterieId}</span>
      </p>
      <p className="mt-2 text-gray-500">
        (Module à implémenter : chargement d’un bloc et contrôle des critères/doublons)
      </p>
    </div>
  );
}
