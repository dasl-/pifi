import "./SwipeableListItem.css";
import React from "react";
import {ReactComponent as PlayNextIcon} from '../../../play-next-icon-filled.svg';

/**
 * taken from https://github.com/LukasMarx/react-swipeable-list-tutorial
 * https://malcoded.com/posts/react-swipeable-list/
 */
class SwipeableListItem extends React.Component {
  // DOM Refs
  listElement;
  wrapper;
  background;

  // Drag & Drop
  dragStartX = 0;
  left = 0;
  dragged = false;
  dragStartLeft = 0;

  // FPS Limit
  dragStartTime;
  dragStopTime;
  fpsInterval = 1000 / 60;

  constructor(props) {
    super(props);

    this.listElement = null;
    this.wrapper = null;
    this.background = null;
    this.buttons = []
    this.isMenuOpen = false;

    this.onMouseMove = this.onMouseMove.bind(this);
    this.onTouchMove = this.onTouchMove.bind(this);
    this.onDragStartMouse = this.onDragStartMouse.bind(this);
    this.onDragStartTouch = this.onDragStartTouch.bind(this);
    this.onDragEndMouse = this.onDragEndMouse.bind(this);
    this.onDragEndTouch = this.onDragEndTouch.bind(this);
    this.onDragEnd = this.onDragEnd.bind(this);
    this.updatePosition = this.updatePosition.bind(this);

    this.onSwiped = this.onSwiped.bind(this);

    this.state = {
      left: 0,
    }
  }

  componentDidMount() {
    window.addEventListener("mouseup", this.onDragEndMouse);
    window.addEventListener("touchend", this.onDragEndTouch);
  }

  componentWillUnmount() {
    window.removeEventListener("mouseup", this.onDragEndMouse);
    window.removeEventListener("touchend", this.onDragEndTouch);
  }

  onDragStartMouse(evt) {
    this.onDragStart(evt.clientX);
    window.addEventListener("mousemove", this.onMouseMove);
  }

  onDragStartTouch(evt) {
    const touch = evt.changedTouches[0];
    this.onDragStart(touch.clientX);
    window.addEventListener("touchmove", this.onTouchMove);
  }

  onDragStart(clientX) {
    this.dragged = true;
    this.dragStartX = clientX;
    this.dragStartLeft = this.state.left;
    this.listElement.className = "ListItem";
    this.dragStartTime = Date.now();
    this.buttons.forEach(button => button.style.transition = 'width 0s ease-out');
    requestAnimationFrame(this.updatePosition);
  }

  onDragEndMouse(evt) {
    window.removeEventListener("mousemove", this.onMouseMove);
    this.onDragEnd(evt.clientX);
  }

  onDragEndTouch(evt) {
    const touch = evt.changedTouches[0];
    window.removeEventListener("touchmove", this.onTouchMove);
    this.onDragEnd(touch.clientX);
  }

  onDragEnd(clientX) {
    if (this.dragged) {
      this.dragged = false;
      this.dragStopTime = Date.now();

      const fullSwipeThreshold = this.props.fullSwipeThreshold || 0.5;
      const openMenuSwipeThreshold = this.props.openMenuSwipeThreshold || 0.3;
      const closeMenuSwipeThreshold = this.props.closeMenuSwipeThreshold || 0.3;
      if (this.state.left < this.listElement.offsetWidth * fullSwipeThreshold * -1) {
        // full left swipe
        this.setState({left: -this.listElement.offsetWidth * 2});
        this.wrapper.style.maxHeight = 0;
        this.onSwiped();
      } else if (!this.isMenuOpen) {
        if (this.state.left < this.listElement.offsetWidth * openMenuSwipeThreshold * -1) {
          // partial left swipe: we swiped to reveal menu with buttons
          this.isMenuOpen = true;
          this.setState({left: this.props.numButtons * -this.props.buttonWidth});
        } else {
          // no swipe registered
          this.setState({left: 0});
        }
      } else if (this.isMenuOpen) {
        const wasDragDirectionRight = this.dragStartX - clientX < 0;
        const positionPctDelta = this.dragStartLeft / this.listElement.offsetWidth - this.state.left / this.listElement.offsetWidth;
        if (wasDragDirectionRight && -1 * positionPctDelta > closeMenuSwipeThreshold) {
          // we swiped right hard enough to close the menu
          this.isMenuOpen = false;
          this.setState({left: 0});
        } else {
          // menu is still open. Don't adjust this.isMenuOpen.
          this.setState({left: this.props.numButtons * -this.props.buttonWidth});
        }
      }

      this.listElement.className = "BouncingListItem";
      this.listElement.style.transform = `translateX(${this.state.left}px)`;
      this.buttons.forEach(button => button.style.transition = this.wrapper.style.transition);
    }
  }

  onMouseMove(evt) {
    const leftDelta = evt.clientX - this.dragStartX;
    const newLeft = leftDelta + this.dragStartLeft;
    if (newLeft < 0) { // don't allow swiping right past the boundary
      this.setState({left: newLeft});
    }
  }

  onTouchMove(evt) {
    const touch = evt.targetTouches[0];
    const leftDelta = touch.clientX - this.dragStartX;
    const newLeft = leftDelta + this.dragStartLeft;
    if (newLeft < 0) { // don't allow swiping right past the boundary
      this.setState({left: newLeft});
    }
  }

  updatePosition() {
    if (this.dragged) {
      requestAnimationFrame(this.updatePosition);
    }

    const now = Date.now();
    const elapsed = now - this.dragStartTime;

    if (elapsed > this.fpsInterval) {
      this.listElement.style.transform = `translateX(${this.state.left}px)`;
      this.dragStartTime = Date.now();
    }
  }

  onSwiped() {
    if (this.props.onSwipe) {
      this.props.onSwipe();
    }
  }

  render() {
    this.buttons.forEach(button => button.style.width = -this.state.left / this.props.numButtons + "px");
    return (
      <div className="Wrapper" ref={div => (this.wrapper = div)}>
        <div ref={div => (this.background = div)} className="Background">
          {
            this.props.index !== 0 &&
            <div
              ref={div => {this.buttons[1] = div}}
              className="swipeable-list-item-button play-next"
              onClick={this.props.onPlayVideoNext}
            >
              <PlayNextIcon className='play-next-icon' />
            </div>
          }
          <div
            ref={div => {this.buttons[0] = div}}
            className="swipeable-list-item-button remove-video"
            onClick={this.props.onRemoveVideo}
          >
            <span className='glyphicon glyphicon-fill-no-stroke glyphicon-trash bg-light-text' aria-hidden='true' />
          </div>
        </div>
        <div
          ref={div => (this.listElement = div)}
          onMouseDown={this.onDragStartMouse}
          onTouchStart={this.onDragStartTouch}
          className="ListItem"
        >
          {this.props.children}
        </div>
      </div>
    );
  }
}

export default SwipeableListItem;
