import { Button, Result } from 'antd';

export default function Exception404Page() {
  return (
    <Result
      status="404"
      title="页面不存在"
      subTitle="当前路由未在 AI Brain Ant Design Pro 工作台中注册。"
      extra={
        <Button type="primary" onClick={() => window.location.assign('/delivery/rd-tasks')}>
          回到研发任务
        </Button>
      }
    />
  );
}
