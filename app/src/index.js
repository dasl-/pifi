import React from 'react';
import ReactDOM from 'react-dom';

import App from 'component/app';
import InvalidBuild from 'component/invalid_build';

import 'css/bootstrap.min.css';
import 'css/bootstrap.darkly2.css';
import 'css/main.css';

if (!process.env.REACT_APP_API_BASE_URL) {
  ReactDOM.render(
    <InvalidBuild />,
    document.getElementById('root')
  );
} else {
  ReactDOM.render(
    <App />,
    document.getElementById('root')
  );
}