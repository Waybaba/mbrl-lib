import numpy as np
from gymnasium.spaces import Box
from gymnasium import utils
from gymnasium.envs.mujoco import mujoco_env


# Obtained from https://github.com/JannerM/mbpo/blob/master/mbpo/env/ant.py
class AntTruncatedObsEnv(mujoco_env.MujocoEnv, utils.EzPickle):
    metadata = {
        "render_modes": [
            "human",
            "rgb_array",
            "depth_array",
        ],
        "render_fps": 20,
    }
    def __init__(self, render_mode: str = None):
        observation_space = Box(
            low=-np.inf, high=np.inf, shape=(27,), dtype=np.float64
        )
        mujoco_env.MujocoEnv.__init__(self, "ant.xml", 5, observation_space, render_mode=render_mode)
        utils.EzPickle.__init__(self)

    def step(self, a):
        xposbefore = self.get_body_com("torso")[0]
        self.do_simulation(a, self.frame_skip)
        xposafter = self.get_body_com("torso")[0]
        forward_reward = (xposafter - xposbefore) / self.dt
        ctrl_cost = 0.5 * np.square(a).sum()
        contact_cost = (
            0.5 * 1e-3 * np.sum(np.square(np.clip(self.data.cfrc_ext, -1, 1)))
        )
        survive_reward = 1.0
        reward = forward_reward - ctrl_cost - contact_cost + survive_reward
        state = self.state_vector()
        notterminated = np.isfinite(state).all() and state[2] >= 0.2 and state[2] <= 1.0
        terminated = not notterminated
        ob = self._get_obs()

        if self.render_mode == "human":
            self.render()

        return (
            ob,
            reward,
            terminated,
            False,
            dict(
                reward_forward=forward_reward,
                reward_ctrl=-ctrl_cost,
                reward_contact=-contact_cost,
                reward_survive=survive_reward,
            ),
        )

    def _get_obs(self):
        return np.concatenate(
            [
                self.data.qpos.flat[2:],
                self.data.qvel.flat,
                # np.clip(self.data.cfrc_ext, -1, 1).flat,
            ]
        )

    def reset_model(self):
        qpos = self.init_qpos + self.np_random.uniform(
            size=self.model.nq, low=-0.1, high=0.1
        )
        qvel = self.init_qvel + self.np_random.standard_normal(self.model.nv) * 0.1
        self.set_state(qpos, qvel)
        return self._get_obs()

    def viewer_setup(self):
        self.viewer.cam.distance = self.model.stat.extent * 0.5
