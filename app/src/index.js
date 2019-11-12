import React from 'react';
import { render } from 'react-dom';
import App from 'component/app/app';
import InvalidBuild from 'component/app/invalid_build';

import utils from 'utils';

import 'css/main.css';
import 'css/bootstrap.min.css';
import 'css/custom-theme.css';

if (process.env.REACT_APP_GOOGLE_API_KEY && process.env.REACT_APP_GOOGLE_API_CLIENT_ID) {
  render(
    <App
      is_new_session={!utils.hasExistingSession()}
    />,
    document.getElementById('root')
  );
} else {
  render(
    <InvalidBuild />,
    document.getElementById('root')
  );
}
