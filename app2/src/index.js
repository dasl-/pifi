import React from 'react'
import { render } from 'react-dom'
import App from 'component/app/app';

import utils from 'utils';

import 'css/main.css';
import 'css/creative.min.css';

render(
  <App
    is_new_session={!utils.hasExistingSession()}
  />,
  document.getElementById('root')
)