import { useEffect } from "react";

import { DashboardPage } from "@/pages/dashboard";
import { useTriageStore } from "@/store/useTriageStore";

function App() {
  const loadTasks = useTriageStore((state) => state.loadTasks);
  const resetEnv = useTriageStore((state) => state.resetEnv);
  const tasks = useTriageStore((state) => state.tasks);

  useEffect(() => {
    void loadTasks();
  }, [loadTasks]);

  useEffect(() => {
    if (tasks.length > 0) {
      void resetEnv(tasks[0].task_id);
    }
  }, [tasks, resetEnv]);

  return <DashboardPage />;
}

export default App;
