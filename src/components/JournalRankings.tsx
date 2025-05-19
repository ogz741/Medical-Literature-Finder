import React, { useState } from 'react';
import { useQuery } from 'react-query';
import axios from 'axios';

interface JournalRanking {
  rank: number;
  journal_name: string;
  impact_factor: number;
}

function JournalRankings() {
  const [specialty, setSpecialty] = useState('Ophthalmology');

  const { data: rankings, isLoading, error } = useQuery<JournalRanking[]>(
    ['rankings', specialty],
    async () => {
      const response = await axios.get(`/api/rankings/${specialty}`);
      return response.data;
    }
  );

  const specialties = [
    "Allergy", "Andrology", "Anesthesiology", "Cardiology", "Dermatology",
    "Emergency Medicine", "Endocrinology", "Gastroenterology", "Geriatrics",
    "Gynecology", "Hematology", "Immunology", "Infectious Diseases",
    "Internal Medicine", "Nephrology", "Neurology", "Neurosurgery",
    "Obstetrics", "Oncology", "Ophthalmology", "Orthopedics",
    "Otolaryngology", "Pathology", "Pediatrics", "Physical Medicine",
    "Plastic Surgery", "Psychiatry", "Pulmonology", "Radiology",
    "Rheumatology", "Sports Medicine", "Surgery", "Toxicology",
    "Transplantation", "Urology", "Vascular Medicine"
  ];

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold">Journal Rankings</h2>
        <select
          className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
          value={specialty}
          onChange={(e) => setSpecialty(e.target.value)}
        >
          {specialties.map(spec => (
            <option key={spec} value={spec}>{spec}</option>
          ))}
        </select>
      </div>

      {isLoading && (
        <div className="text-center py-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading rankings...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-600">Error loading rankings. Please try again.</p>
        </div>
      )}

      {rankings && (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Rank
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Journal Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Impact Factor
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {rankings.map((journal) => (
                <tr key={journal.journal_name}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {journal.rank}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {journal.journal_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {journal.impact_factor.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default JournalRankings;