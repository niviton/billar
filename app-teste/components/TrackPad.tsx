import React from 'react';
import { Track } from '../types';

interface TrackPadProps {
  track: Track;
  onToggle: (id: string) => void;
}

const TrackPad: React.FC<TrackPadProps> = ({ track, onToggle }) => {
  return (
    <button
      onClick={() => onToggle(track.id)}
      className={`
        relative group h-32 rounded-2xl transition-all duration-300 transform active:scale-95
        ${track.isActive 
          ? 'scale-105 shadow-xl ring-4 ring-offset-2' 
          : 'bg-white shadow-md hover:shadow-lg hover:-translate-y-1'
        }
      `}
      style={{
        backgroundColor: track.isActive ? track.color : undefined,
        borderColor: track.isActive ? 'transparent' : track.color,
        borderWidth: track.isActive ? 0 : '2px',
        ['--tw-ring-color' as any]: track.color
      }}
    >
      <div className="flex flex-col items-center justify-center p-4">
        <span className={`text-xs font-bold uppercase tracking-widest mb-2 ${track.isActive ? 'text-white' : 'text-gray-400'}`}>
          {track.type}
        </span>
        <span className={`text-sm font-medium ${track.isActive ? 'text-white' : 'text-gray-800'}`}>
          {track.name}
        </span>
      </div>
      
      {track.isActive && (
        <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-white animate-ping" />
      )}
    </button>
  );
};

export default TrackPad;