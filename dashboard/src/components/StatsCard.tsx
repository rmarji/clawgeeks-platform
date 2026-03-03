interface StatsCardProps {
  title: string
  value: string | number
  icon: string
  color?: 'default' | 'green' | 'yellow' | 'red' | 'blue'
}

const colorClasses = {
  default: 'bg-slate-100 text-slate-600',
  green: 'bg-green-100 text-green-600',
  yellow: 'bg-yellow-100 text-yellow-600',
  red: 'bg-red-100 text-red-600',
  blue: 'bg-blue-100 text-blue-600',
}

export default function StatsCard({ 
  title, 
  value, 
  icon, 
  color = 'default' 
}: StatsCardProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-500 mb-1">{title}</p>
          <p className="text-2xl font-bold text-slate-900">{value}</p>
        </div>
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center text-xl ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
    </div>
  )
}
