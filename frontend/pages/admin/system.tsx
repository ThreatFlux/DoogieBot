import { useState, useEffect } from 'react';
import AdminLayout from '@/components/layout/AdminLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { getSystemSettings, updateSystemSettings, LogLevel } from '@/services/system';
import withAdmin from '@/utils/withAdmin';
import { useErrorHandler } from '@/hooks/useErrorHandler';

function SystemSettings() {
  const [disableSqlLogs, setDisableSqlLogs] = useState<boolean>(false);
  const [logLevel, setLogLevel] = useState<LogLevel>('INFO');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const { handleError } = useErrorHandler();

  // Available log levels
  const logLevels: LogLevel[] = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];

  // Load system settings
  useEffect(() => {
    const loadSettings = async () => {
      setIsLoading(true);
      try {
        const response = await getSystemSettings();
        if (response.data) {
          setDisableSqlLogs(response.data.settings.disable_sql_logs || false);
          if (response.data.settings.log_level) {
            setLogLevel(response.data.settings.log_level);
          }
        }
      } catch (error) {
        handleError(error, 'Failed to load system settings');
      } finally {
        setIsLoading(false);
      }
    };

    loadSettings();
  }, [handleError]);

  // Handle toggle change
  const handleToggleSqlLogs = async () => {
    setIsSaving(true);
    setMessage(null);
    
    try {
      const newValue = !disableSqlLogs;
      const response = await updateSystemSettings({ disable_sql_logs: newValue });
      
      if (response.data) {
        setDisableSqlLogs(response.data.settings.disable_sql_logs || false);
        setMessage('Settings updated successfully');
      }
    } catch (error) {
      handleError(error, 'Failed to update system settings');
    } finally {
      setIsSaving(false);
    }
  };

  // Handle log level change
  const handleLogLevelChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLevel = e.target.value as LogLevel;
    setIsSaving(true);
    setMessage(null);
    
    try {
      const response = await updateSystemSettings({ log_level: newLevel });
      
      if (response.data) {
        setLogLevel(response.data.settings.log_level || 'INFO');
        setMessage('Log level updated successfully');
      }
    } catch (error) {
      handleError(error, 'Failed to update log level');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <AdminLayout title="System Settings - Doogie Chat Bot">
      <h1 className="text-3xl font-bold mb-6">System Settings</h1>
      
      {message && (
        <div className="mb-6 p-4 bg-green-100 dark:bg-green-900/30 border border-green-400 dark:border-green-800 text-green-700 dark:text-green-400 rounded-md">
          {message}
        </div>
      )}
      
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Logging Settings</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-medium">Disable SQLAlchemy Logging</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  When enabled, SQLAlchemy query logs will be completely hidden (set to WARNING level), making it easier to see other debug information.
                </p>
              </div>
              <div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={disableSqlLogs}
                    onChange={handleToggleSqlLogs}
                    disabled={isLoading || isSaving}
                  />
                  <div className={`w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600 ${isSaving ? 'opacity-50' : ''}`}></div>
                </label>
              </div>
            </div>
            
            <div>
              <h3 className="text-lg font-medium mb-2">Application Log Level</h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
                Set the log level for the application. Higher levels show fewer, more important logs.
                <span className="block mt-1 italic">Note: This setting does not affect SQLAlchemy logging, which is controlled separately by the toggle above.</span>
              </p>
              <div className="max-w-xs">
                <select
                  value={logLevel}
                  onChange={handleLogLevelChange}
                  disabled={isLoading || isSaving}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:text-white"
                >
                  {logLevels.map((level) => (
                    <option key={level} value={level}>
                      {level}
                    </option>
                  ))}
                </select>
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                  {logLevel === 'DEBUG' && 'Shows all logs including detailed debugging information'}
                  {logLevel === 'INFO' && 'Shows informational messages, warnings, and errors'}
                  {logLevel === 'WARNING' && 'Shows only warnings and errors'}
                  {logLevel === 'ERROR' && 'Shows only errors'}
                  {logLevel === 'CRITICAL' && 'Shows only critical errors'}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </AdminLayout>
  );
}

export default withAdmin(SystemSettings, "System Settings - Doogie Chat Bot");